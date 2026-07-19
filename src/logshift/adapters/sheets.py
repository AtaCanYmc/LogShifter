import asyncio
import logging
from typing import Any, Dict, List

from logshift.core.adapter import TransportAdapter
from logshift.core.exceptions import AdapterError

logger = logging.getLogger("logshift.adapters.sheets")


class SheetsAdapter(TransportAdapter):
    """
    SheetsAdapter appends log rows to a Google Sheet using gspread.
    """

    def __init__(
        self,
        service_account_file: str,
        spreadsheet_id: str,
        worksheet_name: str = "Logs",
        name: str = "sheets",
        config: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name, config)
        self.service_account_file = service_account_file
        self.spreadsheet_id = spreadsheet_id
        self.worksheet_name = worksheet_name

    async def ship(self, logs: List[Dict[str, Any]], target: str, **kwargs: Any) -> bool:
        """
        Ships logs to a Google Spreadsheet.

        Args:
            logs: List of log dicts.
            target: Spreadsheet ID (fallback/override).
            **kwargs: Includes dry_run parameter.
        """
        dry_run = kwargs.get("dry_run", False)
        spreadsheet_id = target or self.spreadsheet_id

        if not spreadsheet_id:
            raise AdapterError("Google Spreadsheet ID is required.")

        # Header Columns
        headers = ["ID", "Timestamp", "Level", "Message", "Payload"]

        # Format logs to matching rows
        rows: List[List[Any]] = []
        for log in logs:
            attributes = log.get("attributes", {})
            row = [
                str(attributes.get("id", "")),
                str(log.get("timestamp", "")),
                str(log.get("severity_text", "")),
                str(log.get("body", "")),
                str(
                    {
                        "attributes": attributes,
                        "severity_number": log.get("severity_number"),
                        "trace_id": log.get("trace_id"),
                        "span_id": log.get("span_id"),
                    }
                ),
            ]
            rows.append(row)

        if dry_run:
            logger.info("---------------- DRY-RUN SIMULATION ----------------")
            logger.info(f"[Dry-Run Sheets] Target Spreadsheet: {spreadsheet_id}")
            logger.info(f"[Dry-Run Sheets] Worksheet Name: {self.worksheet_name}")
            logger.info(f"[Dry-Run Sheets] Headers: {headers}")
            logger.info(f"[Dry-Run Sheets] Appending {len(rows)} rows.")
            logger.info(f"[Dry-Run Sheets] Rows sample: {rows[:2]}")
            logger.info("----------------------------------------------------")
            return True

        if not self.service_account_file:
            raise AdapterError("Service Account JSON file is required.")

        return await asyncio.to_thread(self._append_to_sheets, spreadsheet_id, headers, rows)

    def _append_to_sheets(
        self, spreadsheet_id: str, headers: List[str], rows: List[List[Any]]
    ) -> bool:
        import gspread

        try:
            gc = gspread.service_account(filename=self.service_account_file)
            sh = gc.open_by_key(spreadsheet_id)

            # Try to get worksheet or create it if not exists
            try:
                wks = sh.worksheet(self.worksheet_name)
            except gspread.exceptions.WorksheetNotFound:
                wks = sh.add_worksheet(
                    title=self.worksheet_name, rows="1000", cols=str(len(headers))
                )
                # Append headers
                wks.append_row(headers)
                logger.info(f"Created new worksheet '{self.worksheet_name}' with headers.")

            # Batch append rows
            wks.append_rows(rows, value_input_option="USER_ENTERED")
            logger.info(f"Successfully appended {len(rows)} log rows to Google Sheets.")
            return True
        except Exception as e:
            raise AdapterError(f"Failed to append rows to Google Sheets: {e}") from e
