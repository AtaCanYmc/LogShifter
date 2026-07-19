import asyncio
import logging
from typing import Any, Dict, List, Optional

from logshift.core.exceptions import ConfigurationError, LogshiftError

logger = logging.getLogger("logshift.core.fetcher")


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
        Fetches logs from Supabase utilizing cursor-based pagination.
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
                query = self.client.table(table_name).select("*")

                if start_date:
                    query = query.gt(date_column, start_date)
                if end_date:
                    query = query.lt(date_column, end_date)

                if last_id is not None:
                    query = query.gt(cursor_column, last_id)

                query = query.order(cursor_column, desc=False).limit(chunk_size)

                response = query.execute()
                data = response.data

                if not data:
                    break

                all_logs.extend(data)
                logger.info(f"Fetched {len(data)} records. Last cursor value: {last_id}. Total so far: {len(all_logs)}")

                last_record = data[-1]
                last_id = last_record.get(cursor_column)

                if len(data) < chunk_size:
                    break

            return all_logs

        except Exception as e:
            raise LogshiftError(f"Failed to fetch logs from Supabase: {e}") from e
