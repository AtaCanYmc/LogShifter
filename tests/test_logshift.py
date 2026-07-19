import pytest
import asyncio
from logshift.core import LogshiftError, LogManager, AdapterError, TransportAdapter
from logshift.adapters.sheets import SheetsAdapter
from logshift.adapters.telegram import TelegramAdapter


def test_error_definitions():
    assert issubclass(LogshiftError, Exception)


def test_log_manager_initialization():
    manager = LogManager(dry_run=True, max_retries=2)
    assert manager.dry_run is True
    assert manager.max_retries == 2
    assert len(manager.registered_adapters) == 0


def test_adapters_dry_run_initialization():
    sheets_adapter = SheetsAdapter(
        service_account_file="credentials.json",
        spreadsheet_id="spread_123",
        worksheet_name="TestLogs"
    )
    assert sheets_adapter.spreadsheet_id == "spread_123"
    assert sheets_adapter.worksheet_name == "TestLogs"

    telegram_adapter = TelegramAdapter(
        bot_token="token_123",
        chat_id="chat_123"
    )
    assert telegram_adapter.bot_token == "token_123"
    assert telegram_adapter.chat_id == "chat_123"


class MockFlakyAdapter(TransportAdapter):
    def __init__(self, name="flaky"):
        super().__init__(name)
        self.attempts = 0

    async def ship(self, logs, target, **kwargs):
        self.attempts += 1
        raise ValueError("Flake error")


@pytest.mark.asyncio
async def test_retry_mechanism_error():
    manager = LogManager(dry_run=False, max_retries=3, initial_delay=0.01, backoff=1.5)
    adapter = MockFlakyAdapter()
    manager.register_adapter(adapter)

    with pytest.raises(AdapterError):
        await manager.ship([{"msg": "test"}], {"flaky": "target"})
    
    # Verify that it retried 3 times
    assert adapter.attempts == 3
