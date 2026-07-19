from abc import ABC, abstractmethod
from typing import Any, Dict, List


class TransportAdapter(ABC):
    """
    Abstract base class for all transport adapters.
    
    Any new storage/notification target must implement this class
    and register with LogManager to be used in logport SDK.
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
            target: The destination identifier (e.g. repo name, channel ID, sheet name).
            **kwargs: Extra parameters depending on the adapter implementation.
            
        Returns:
            bool: True if successful, False or raises AdapterError otherwise.
        """
        pass
