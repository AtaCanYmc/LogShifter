import asyncio
import logging
from typing import Any, Dict, List, Optional
from logshift.core.exceptions import ConfigurationError, LogshiftError

logger = logging.getLogger("logshift.fetcher")


class LogFetcher:
    """
    LogFetcher retrieves log entries from a Supabase database table in a chunked, 
    memory-efficient manner.
    """

    def __init__(self, supabase_url: str, supabase_key: str) -> None:
        """
        Args:
            supabase_url: The Supabase project URL.
            supabase_key: The Supabase API/Service key.
        """
        if not supabase_url or not supabase_key:
            raise ConfigurationError("Supabase URL and API Key must be provided.")
        
        # Defer import to avoid supabase module loading overhead when not fetching
        from supabase import create_client, Client
        self.client: Client = create_client(supabase_url, supabase_key)

    async def fetch_logs(
        self,
        table_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        date_column: str = "created_at",
        chunk_size: int = 1000,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """
        Fetches logs from the Supabase table, utilizing pagination to handle 
        large datasets efficiently.
        
        Args:
            table_name: The name of the Supabase table.
            start_date: Optional start datetime string (e.g. ISO format).
            end_date: Optional end datetime string.
            date_column: The database column used for date filtering.
            chunk_size: Number of records to fetch per query.
            
        Returns:
            List[Dict[str, Any]]: List of log records retrieved.
        """
        return await asyncio.to_thread(
            self._execute_fetch, table_name, start_date, end_date, date_column, chunk_size, **kwargs
        )

    def _execute_fetch(
        self,
        table_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        date_column: str = "created_at",
        chunk_size: int = 1000,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        all_logs: List[Dict[str, Any]] = []
        offset = 0

        logger.info(f"Starting fetch from table '{table_name}'...")

        try:
            while True:
                # Build the query
                query = self.client.table(table_name).select("*")

                if start_date:
                    query = query.gt(date_column, start_date)
                if end_date:
                    query = query.lt(date_column, end_date)

                # Paginate using range
                start = offset
                end = offset + chunk_size - 1
                query = query.range(start, end)

                response = query.execute()
                data = response.data

                if not data:
                    break

                all_logs.extend(data)
                logger.info(f"Fetched {len(data)} records (range {start} to {end}). Total fetched: {len(all_logs)}")

                if len(data) < chunk_size:
                    # Last page reached
                    break

                offset += chunk_size

            return all_logs

        except Exception as e:
            raise LogshiftError(f"Failed to fetch logs from Supabase: {e}") from e
