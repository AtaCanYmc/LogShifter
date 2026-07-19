import asyncio
import os
import sys

# Adjust path to import local logshift package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from logshift.adapters.telegram import TelegramAdapter


async def main():
    print("--- Running Telegram Adapter Demo ---")

    # Instantiate adapter in dry-run mode
    adapter = TelegramAdapter(
        bot_token="dummy_bot_token", chat_id="dummy_chat_id", name="telegram_demo"
    )

    # Simulated OpenTelemetry format log record
    logs = [
        {
            "timestamp": "2026-07-19T12:00:00Z",
            "severity_text": "ERROR",
            "severity_number": 17,
            "body": "Database connection timeout",
            "attributes": {"database_host": "db.example.com"},
            "trace_id": "xyz987trace",
            "span_id": "span456",
        }
    ]

    # Run in dry-run (simulation) mode
    print("Running dry-run simulation:")
    await adapter.ship(logs=logs, target="dummy_chat_id", dry_run=True)

    print("\nTo run in production mode:")
    print("1. Set real telegram parameters")
    print("2. Call: await adapter.ship(logs, target='real_chat_id', dry_run=False)")


if __name__ == "__main__":
    asyncio.run(main())
