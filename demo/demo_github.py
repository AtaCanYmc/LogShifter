import asyncio
import os
import sys

# Adjust path to import local logshift package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from logshift.adapters.github import GitHubAdapter


async def main():
    print("--- Running GitHub Adapter Demo ---")

    # Instantiate adapter in dry-run mode
    adapter = GitHubAdapter(token="ghp_dummyTokenForSimulationOnly", name="github_demo")

    # Simulated OpenTelemetry format log record
    logs = [
        {
            "timestamp": "2026-07-19T12:00:00Z",
            "severity_text": "INFO",
            "severity_number": 9,
            "body": "User logged in successfully",
            "attributes": {"user_id": 42},
            "trace_id": "abc123trace",
            "span_id": "span123",
        }
    ]

    # Run in dry-run (simulation) mode
    print("Running dry-run simulation:")
    await adapter.ship(
        logs=logs,
        target="username/my-log-archive",
        dry_run=True,
        path="logs/archive.json",
        branch="main",
        message="Simulated commit from GitHubAdapter",
    )

    print("\nTo run in production mode:")
    print("1. Set real parameters (actual token & repository target)")
    print("2. Call: await adapter.ship(logs, target='owner/repo', dry_run=False)")


if __name__ == "__main__":
    asyncio.run(main())
