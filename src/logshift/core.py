import asyncio
from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("logshift.core")


# Custom Exceptions
class LogshiftError(Exception):
    """Base exception for all logshift related errors."""
    pass


class ConfigurationError(LogshiftError):
    """Raised when there is a configuration-related error."""
    pass


class AdapterError(LogshiftError):
    """Raised when a TransportAdapter fails to ship/archive logs."""
    pass


# Base Transport Adapter
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


# Log Manager
class LogManager:
    """
    LogManager orchestrates the transport adapters and dispatches logs to them,
    with built-in dry_run capability.
    """

    def __init__(
        self,
        dry_run: bool = False,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff: float = 2.0
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
        self,
        logs: List[Dict[str, Any]],
        targets: Dict[str, str],
        **kwargs: Any
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

        raise AdapterError(f"Error in adapter '{adapter.name}': {last_exception}") from last_exception


# Cursor-Based Log Fetcher
class LogFetcher:
    """
    LogFetcher retrieves log entries from a Supabase database table in a chunked, 
    memory-efficient manner using cursor-based pagination (ID-based progression).
    """

    def __init__(self, supabase_url: str, supabase_key: str) -> None:
        if not supabase_url or not supabase_key:
            raise ConfigurationError("Supabase URL and API Key must be provided.")
        
        # Defer import to keep core lightweight
        from supabase import create_client, Client
        self.client: Client = create_client(supabase_url, supabase_key)

    async def fetch_logs(
        self,
        table_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        date_column: str = "created_at",
        cursor_column: str = "id",
        chunk_size: int = 1000,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """
        Fetches logs from Supabase utilizing cursor-based pagination (sorting by ID 
        and progressing to avoid offset performance penalties).
        """
        return await asyncio.to_thread(
            self._execute_fetch, table_name, start_date, end_date, date_column, cursor_column, chunk_size, **kwargs
        )

    def _execute_fetch(
        self,
        table_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        date_column: str = "created_at",
        cursor_column: str = "id",
        chunk_size: int = 1000,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        all_logs: List[Dict[str, Any]] = []
        last_id: Optional[Any] = None

        logger.info(f"Starting cursor-based fetch from table '{table_name}' using cursor '{cursor_column}'...")

        try:
            while True:
                # Query initialization
                query = self.client.table(table_name).select("*")

                # Filter by date ranges if provided
                if start_date:
                    query = query.gt(date_column, start_date)
                if end_date:
                    query = query.lt(date_column, end_date)

                # Cursor logic: get logs with cursor value greater than the last processed record
                if last_id is not None:
                    query = query.gt(cursor_column, last_id)

                # Sort by cursor column ASC and limit
                query = query.order(cursor_column, desc=False).limit(chunk_size)

                response = query.execute()
                data = response.data

                if not data:
                    break

                all_logs.extend(data)
                logger.info(f"Fetched {len(data)} records. Last cursor value: {last_id}. Total so far: {len(all_logs)}")

                # Get the cursor value from the last element to use on the next iteration
                last_record = data[-1]
                last_id = last_record.get(cursor_column)

                if len(data) < chunk_size:
                    # Last chunk retrieved
                    break

            return all_logs

        except Exception as e:
            raise LogshiftError(f"Failed to fetch logs from Supabase: {e}") from e
