import pytest
from logshift.core import LogshiftError, LogManager
from logshift.config import LogshiftSettings


def test_error_definitions():
    """Verify that custom exception classes are defined correctly."""
    assert issubclass(LogshiftError, Exception)


def test_log_manager_initialization():
    """Verify LogManager properties and dry-run flag default setting."""
    manager = LogManager(dry_run=True)
    assert manager.dry_run is True
    assert len(manager.registered_adapters) == 0


def test_settings_mock_construct():
    """Verify LogshiftSettings can be constructed with mock values."""
    settings = LogshiftSettings.model_construct(
        supabase_url="https://dummy.supabase.co",
        supabase_key="dummy-key",
        logshift_github_token="dummy-token",
        logshift_github_repo="dummy/repo"
    )
    assert settings.supabase_url == "https://dummy.supabase.co"
    assert settings.logshift_github_token == "dummy-token"
