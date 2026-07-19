import asyncio
import logging
from typing import Any, Dict, List, Set

from logshift.core.adapter import TransportAdapter
from logshift.core.exceptions import AdapterError

logger = logging.getLogger("logshift.core.manager")


class LogManager:
    """
    LogManager orchestrates the transport adapters and dispatches logs to them,
    with built-in dry_run capability and retry loops.
    """

    def __init__(
        self,
        dry_run: bool = False,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff: float = 2.0,
    ) -> None:
        self._adapters: Dict[str, TransportAdapter] = {}
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

    @property
    def registered_adapters(self) -> Set[str]:
        return set(self._adapters.keys())

    async def ship(
        self, logs: List[Dict[str, Any]], targets: Dict[str, str], **kwargs: Any
    ) -> Dict[str, bool]:
        """
        Ships logs concurrently to selected registered adapters.
        """
        tasks = []
        adapter_names = []

        for adapter_name, target in targets.items():
            if adapter_name not in self._adapters:
                logger.error(f"Cannot ship to unregistered adapter: {adapter_name}")
                continue

            adapter = self._adapters[adapter_name]
            tasks.append(self._ship_safe(adapter, logs, target, **kwargs))
            adapter_names.append(adapter_name)

        if not tasks:
            logger.warning("No valid transport targets specified for shipping.")
            return {}

        results = await asyncio.gather(*tasks, return_exceptions=True)

        report = {}
        for name, result in zip(adapter_names, results):
            if isinstance(result, Exception):
                logger.error(f"Adapter '{name}' failed with exception: {result}")
                report[name] = False
            else:
                report[name] = result

        return report

    async def _ship_safe(
        self, adapter: TransportAdapter, logs: List[Dict[str, Any]], target: str, **kwargs: Any
    ) -> bool:
        delay = self.initial_delay
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                # Inject dry_run parameter into adapter's ship arguments
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
