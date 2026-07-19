import pytest

from logshift.core.adapter import TransportAdapter
from logshift.core.exceptions import LogshiftError
from logshift.core.manager import LogManager


def test_error_definitions():
    assert issubclass(LogshiftError, Exception)


def test_log_manager_initialization():
    manager = LogManager(dry_run=True, max_retries=2)
    assert manager.dry_run is True
    assert manager.max_retries == 2
    assert len(manager.registered_adapters) == 0


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

    report = await manager.ship([{"msg": "test"}], {"flaky": "target"})
    assert report["flaky"] is False

    # Verify that it retried 3 times
    assert adapter.attempts == 3
