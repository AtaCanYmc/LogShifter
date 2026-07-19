# Base Transport Adapter
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class TransportAdapter(ABC):
    """
    Abstract base class for all transport adapters.
    """

    def __init__(self, name: str, config: Dict[str, Any] | None = None) -> None:
        self.name = name
        self.config = config or {}

    @abstractmethod
    async def ship(self, logs: List[Dict[str, Any]], target: str, **kwargs: Any) -> bool:
        """
        Ships logs asynchronously to the destination.

        Args:
            logs: A list of dictionaries representing log entries.
            target: The destination identifier.
            **kwargs: Extra parameters depending on the adapter implementation.
        """
        pass
