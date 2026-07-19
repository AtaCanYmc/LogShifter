import asyncio
import os
import sys

# Adjust path to import local logshift package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from logshift.adapters.discord import DiscordAdapter


async def main():
    print("--- Running Discord Webhook Adapter Demo ---")

    # Instantiate adapter in dry-run mode
    adapter = DiscordAdapter(
        webhook_url="https://discord.com/api/webhooks/dummy/webhook", name="discord_demo"
    )

    # Simulated OpenTelemetry format log record
    logs = [
        {
            "timestamp": "2026-07-19T12:00:00Z",
            "severity_text": "WARNING",
            "severity_number": 13,
            "body": "Disk space usage at 85%",
            "attributes": {"volume": "/dev/sda1"},
            "trace_id": "",
            "span_id": "",
        }
    ]

    # Run in dry-run (simulation) mode
    print("Running dry-run simulation:")
    await adapter.ship(
        logs=logs, target="https://discord.com/api/webhooks/dummy/webhook", dry_run=True
    )

    print("\nTo run in production mode:")
    print("1. Set real Discord Webhook URL")
    print("2. Call: await adapter.ship(logs, target='real_webhook_url', dry_run=False)")


if __name__ == "__main__":
    asyncio.run(main())
