import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

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
        Backward-compatible method returning a flat list of all retrieved logs.
        """
        all_logs: List[Dict[str, Any]] = []
        async for chunk in self.fetch_logs_iter(
            table_name=table_name,
            start_date=start_date,
            end_date=end_date,
            date_column=date_column,
            cursor_column=cursor_column,
            chunk_size=chunk_size,
            **kwargs
        ):
            all_logs.extend(chunk)
        return all_logs

    async def fetch_logs_iter(
        self,
        table_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        date_column: str = "created_at",
        cursor_column: str = "id",
        chunk_size: int = 1000,
        **kwargs: Any
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Asynchronously yields chunks of formatted OpenTelemetry logs page-by-page.
        Ensures a flat memory footprint when reading millions of log lines.
        """
        last_id: Optional[Any] = None
        logger.info(
            f"Starting streaming cursor fetch from '{table_name}' using cursor '{cursor_column}'..."
        )

        try:
            while True:
                # Query one single page in a separate thread to keep loop non-blocking
                page_data = await asyncio.to_thread(
                    self._fetch_page,
                    table_name,
                    last_id,
                    start_date,
                    end_date,
                    date_column,
                    cursor_column,
                    chunk_size,
                    **kwargs
                )

                if not page_data:
                    break

                # Map data to OpenTelemetry Log Record format
                mapped_data = [self._to_opentelemetry_format(row, date_column) for row in page_data]
                yield mapped_data

                logger.info(
                    f"Yielded log page with {len(page_data)} records. Last cursor: {last_id}"
                )

                # Track cursor
                last_record = page_data[-1]
                last_id = last_record.get(cursor_column)

                if len(page_data) < chunk_size:
                    break

        except Exception as e:
            raise LogshiftError(f"Failed to fetch logs from Supabase: {e}") from e

    def _fetch_page(
        self,
        table_name: str,
        last_id: Optional[Any],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        date_column: str = "created_at",
        cursor_column: str = "id",
        chunk_size: int = 1000,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        query = self.client.table(table_name).select("*")

        if start_date:
            query = query.gt(date_column, start_date)
        if end_date:
            query = query.lt(date_column, end_date)

        if last_id is not None:
            query = query.gt(cursor_column, last_id)

        query = query.order(cursor_column, desc=False).limit(chunk_size)

        response = query.execute()
        return response.data

    def _to_opentelemetry_format(self, row: Dict[str, Any], date_column: str) -> Dict[str, Any]:
        """
        Converts a raw database row into OpenTelemetry Log Record format.
        """
        level = str(row.get("level", "INFO")).upper()
        
        severity_map = {
            "TRACE": 1, "VERBOSE": 1,
            "DEBUG": 5,
            "INFO": 9,
            "WARN": 13, "WARNING": 13,
            "ERROR": 17,
            "FATAL": 21, "CRITICAL": 21
        }
        severity_number = severity_map.get(level, 9)

        body = row.get("message") or row.get("body") or ""

        exclude_keys = {date_column, "level", "message", "body", "trace_id", "span_id"}
        attributes = {k: v for k, v in row.items() if k not in exclude_keys}

        return {
            "timestamp": row.get(date_column, ""),
            "severity_text": level,
            "severity_number": severity_number,
            "body": body,
            "attributes": attributes,
            "trace_id": row.get("trace_id", ""),
            "span_id": row.get("span_id", "")
        }
