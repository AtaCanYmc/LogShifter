import asyncio
import os
import sys

# Adjust path to import local logshift package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from logshift.adapters.sheets import SheetsAdapter


async def main():
    print("--- Running Google Sheets Adapter Demo ---")

    # Instantiate adapter in dry-run mode
    adapter = SheetsAdapter(
        service_account_file="credentials.json",
        spreadsheet_id="dummy_spreadsheet_id",
        worksheet_name="Logs",
        name="sheets_demo",
    )

    # Simulated OpenTelemetry format log record
    logs = [
        {
            "timestamp": "2026-07-19T12:00:00Z",
            "severity_text": "INFO",
            "severity_number": 9,
            "body": "User logged in successfully",
            "attributes": {"user_id": 42, "id": 101},
            "trace_id": "abc123trace",
            "span_id": "span123",
        }
    ]

    # Run in dry-run (simulation) mode
    print("Running dry-run simulation:")
    await adapter.ship(logs=logs, target="dummy_spreadsheet_id", dry_run=True)

    print("\nTo run in production mode:")
    print("1. Set real credentials file and spreadsheet ID")
    print("2. Call: await adapter.ship(logs, target='real_sheet_id', dry_run=False)")


if __name__ == "__main__":
    asyncio.run(main())
