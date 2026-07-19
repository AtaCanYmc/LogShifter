import asyncio
import logging
from typing import Any, Dict, List, Set
from logport.core.adapter import TransportAdapter
from logport.core.exceptions import AdapterError

logger = logging.getLogger("logport.manager")


class LogManager:
    """
    LogManager orchestrates the transport adapters and dispatches logs to them.
    
    It supports selective or simultaneous multi-target log shipping.
    """

    def __init__(self) -> None:
        self._adapters: Dict[str, TransportAdapter] = {}

    def register_adapter(self, adapter: TransportAdapter) -> None:
        """
        Registers a transport adapter.
        
        Args:
            adapter: An instance of TransportAdapter.
        """
        if adapter.name in self._adapters:
            logger.warning(f"Overwriting already registered adapter: {adapter.name}")
        self._adapters[adapter.name] = adapter
        logger.info(f"Registered adapter: {adapter.name}")

    def deregister_adapter(self, name: str) -> None:
        """Deregisters an adapter by name."""
        if name in self._adapters:
            del self._adapters[name]
            logger.info(f"Deregistered adapter: {name}")

    def get_adapter(self, name: str) -> TransportAdapter:
        """Retrieves a registered adapter by name."""
        if name not in self._adapters:
            raise KeyError(f"Adapter '{name}' is not registered.")
        return self._adapters[name]

    @property
    def registered_adapters(self) -> Set[str]:
        """Returns the names of all registered adapters."""
        return set(self._adapters.keys())

    async def ship(
        self,
        logs: List[Dict[str, Any]],
        targets: Dict[str, str],
        **kwargs: Any
    ) -> Dict[str, bool]:
        """
        Ships logs concurrently to selected registered adapters.
        
        Args:
            logs: A list of dict logs.
            targets: A dict mapping adapter name to its specific shipping target.
                     Example: {"github": "my-org/logs-repo", "telegram": "-100123456"}
            **kwargs: Extra arguments passed to all adapters.
            
        Returns:
            Dict[str, bool]: A dictionary mapping adapter name to success status.
        """
        tasks = []
        adapter_names = []

        for adapter_name, target in targets.items():
            if adapter_name not in self._adapters:
                logger.error(f"Cannot ship to unregistered adapter: {adapter_name}")
                continue
            
            adapter = self._adapters[adapter_name]
            # Create async task for shipping
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
        self,
        adapter: TransportAdapter,
        logs: List[Dict[str, Any]],
        target: str,
        **kwargs: Any
    ) -> bool:
        try:
            return await adapter.ship(logs, target, **kwargs)
        except Exception as e:
            raise AdapterError(f"Error in adapter '{adapter.name}': {e}") from e
