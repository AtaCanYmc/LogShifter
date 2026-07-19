import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from logshift import LogManager, GitHubAdapter

# Setup logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


async def main():
    # 1. Credentials are explicitly defined/passed as parameters
    print("--- 1. Setting Up Explicit Parameters ---")
    github_token = "mock-github-token-12345"

    # 2. Instantiate LogManager
    print("\n--- 2. Instantiating LogManager ---")
    manager = LogManager()

    # 3. Register GitHubAdapter
    print("\n--- 3. Registering GitHubAdapter ---")
    # We configure it directly by passing the token parameter
    github_adapter = GitHubAdapter(token=github_token, name="github")
    manager.register_adapter(github_adapter)
    print(f"Registered adapters: {manager.registered_adapters}")

    # 4. Prepare Mock Log Data
    print("\n--- 4. Preparing Mock Logs ---")
    mock_logs = [
        {"timestamp": "2026-07-19T19:15:00Z", "level": "INFO", "message": "Supabase sync started."},
        {
            "timestamp": "2026-07-19T19:15:05Z",
            "level": "WARNING",
            "message": "Database latency high: 150ms.",
        },
        {
            "timestamp": "2026-07-19T19:15:10Z",
            "level": "INFO",
            "message": "Successfully retrieved 250 log entries.",
        },
    ]
    print(f"Logs to ship: {mock_logs}")

    # 5. Ship logs (Selective trigger)
    # We will trigger a ship. Note: If the token is fake or mock, it will fail,
    # but we can see the exact error reporting from LogManager.
    print("\n--- 5. Shipping logs asynchronously ---")
    targets = {"github": "dummy-owner/dummy-repo"}

    # We will pass kwargs to configure file path in the commit
    report = await manager.ship(
        logs=mock_logs,
        targets=targets,
        path="logs/2026-07-19_logs.json",
        message="docs: archive logs for 2026-07-19",
    )

    print("\n--- 6. Shipping Report ---")
    for adapter, status in report.items():
        print(f"Adapter: '{adapter}' -> Success: {status}")


if __name__ == "__main__":
    asyncio.run(main())
