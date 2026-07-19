import asyncio
import logging
from typing import Any, Dict, List, Set

from logshift.core.adapter import TransportAdapter
from logshift.core.exceptions import AdapterError

logger = logging.getLogger("logshift.core.manager")


class ShipJob:
    """Represents a log shipping job passed to a worker queue."""

    def __init__(
        self,
        logs: List[Dict[str, Any]],
        target: str,
        kwargs: Dict[str, Any],
        future: asyncio.Future,
    ) -> None:
        self.logs = logs
        self.target = target
        self.kwargs = kwargs
        self.future = future


class LogManager:
    """
    LogManager orchestrates the transport adapters and dispatches logs to them via
    asynchronous workers and queues, isolating retries and rate limit delays.
    """

    def __init__(
        self,
        dry_run: bool = False,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff: float = 2.0,
    ) -> None:
        self._adapters: Dict[str, TransportAdapter] = {}
        self._queues: Dict[str, asyncio.Queue] = {}
        self._workers: Dict[str, asyncio.Task] = {}
        self.dry_run = dry_run
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff = backoff

    def register_adapter(self, adapter: TransportAdapter) -> None:
        if adapter.name in self._adapters:
            logger.warning(f"Overwriting already registered adapter: {adapter.name}")
        self._adapters[adapter.name] = adapter
        logger.info(f"Registered adapter: {adapter.name}")

    def deregister_adapter(self, name: str) -> None:
        if name in self._adapters:
            del self._adapters[name]
            logger.info(f"Deregistered adapter: {name}")
            # Cancel worker if exists
            if name in self._workers:
                self._workers[name].cancel()
                del self._workers[name]
            if name in self._queues:
                del self._queues[name]

    @property
    def registered_adapters(self) -> Set[str]:
        return set(self._adapters.keys())

    async def ship(
        self, logs: List[Dict[str, Any]], targets: Dict[str, str], **kwargs: Any
    ) -> Dict[str, bool]:
        """
        Ships logs concurrently to selected registered adapters using background queues.
        """
        futures = {}

        for adapter_name, target in targets.items():
            if adapter_name not in self._adapters:
                logger.error(f"Cannot ship to unregistered adapter: {adapter_name}")
                continue

            # Ensure background queue and worker are active
            if adapter_name not in self._queues:
                self._queues[adapter_name] = asyncio.Queue()
                self._workers[adapter_name] = asyncio.create_task(
                    self._worker(adapter_name)
                )

            future = asyncio.get_running_loop().create_future()
            job = ShipJob(logs, target, kwargs, future)
            await self._queues[adapter_name].put(job)
            futures[adapter_name] = future

        if not futures:
            logger.warning("No valid transport targets specified for shipping.")
            return {}

        # Wait for all buffered tasks to finish execution
        results = await asyncio.gather(*futures.values(), return_exceptions=True)

        report = {}
        for name, result in zip(futures.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Adapter '{name}' failed with exception: {result}")
                report[name] = False
            else:
                report[name] = result

        return report

    async def _worker(self, adapter_name: str) -> None:
        """Worker task processing jobs sequentially for a specific adapter."""
        queue = self._queues[adapter_name]
        adapter = self._adapters[adapter_name]
        try:
            while True:
                job = await queue.get()
                try:
                    res = await self._ship_safe(
                        adapter, job.logs, job.target, **job.kwargs
                    )
                    job.future.set_result(res)
                except Exception as e:
                    job.future.set_exception(e)
                finally:
                    queue.task_done()
        except asyncio.CancelledError:
            logger.info(f"Worker for '{adapter_name}' cancelled.")

    async def _ship_safe(
        self,
        adapter: TransportAdapter,
        logs: List[Dict[str, Any]],
        target: str,
        **kwargs: Any
    ) -> bool:
        delay = self.initial_delay
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return await adapter.ship(logs, target, dry_run=self.dry_run, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries and not self.dry_run:
                    logger.warning(
                        f"Adapter '{adapter.name}' failed on attempt {attempt}/{self.max_retries}. "
                        f"Retrying in {delay}s... Error: {e}"
                    )
                    await asyncio.sleep(delay)
                    delay *= self.backoff
                else:
                    logger.error(
                        f"Adapter '{adapter.name}' failed permanently after {attempt} attempts."
                    )

        raise AdapterError(
            f"Error in adapter '{adapter.name}': {last_exception}"
        ) from last_exception

    def __del__(self) -> None:
        # Cleanup workers
        for worker in self._workers.values():
            worker.cancel()
