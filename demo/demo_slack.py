import asyncio
import os
import sys

# Adjust path to import local logshift package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from logshift.adapters.slack import SlackAdapter


async def main():
    print("--- Running Slack Webhook Adapter Demo ---")

    # Instantiate adapter in dry-run mode
    adapter = SlackAdapter(
        webhook_url="https://hooks.slack.com/services/dummy/webhook", name="slack_demo"
    )

    # Simulated OpenTelemetry format log record
    logs = [
        {
            "timestamp": "2026-07-19T12:00:00Z",
            "severity_text": "CRITICAL",
            "severity_number": 21,
            "body": "Kubernetes Pod crashed repeatedly (CrashLoopBackOff)",
            "attributes": {"pod_name": "api-gateway-xyz", "namespace": "production"},
            "trace_id": "kube123trace",
            "span_id": "span789",
        }
    ]

    # Run in dry-run (simulation) mode
    print("Running dry-run simulation:")
    await adapter.ship(
        logs=logs, target="https://hooks.slack.com/services/dummy/webhook", dry_run=True
    )

    print("\nTo run in production mode:")
    print("1. Set real Slack Webhook URL")
    print("2. Call: await adapter.ship(logs, target='real_webhook_url', dry_run=False)")


if __name__ == "__main__":
    asyncio.run(main())
