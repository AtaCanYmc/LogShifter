from logshift.core import (
    TransportAdapter,
    LogManager,
    LogFetcher,
    LogshiftError,
    ConfigurationError,
    AdapterError,
)
from logshift.adapters.github import GitHubAdapter
from logshift.adapters.sheets import SheetsAdapter
from logshift.adapters.telegram import TelegramAdapter

__version__ = "0.1.0"
__all__ = [
    "TransportAdapter",
    "LogManager",
    "LogFetcher",
    "LogshiftError",
    "ConfigurationError",
    "AdapterError",
    "GitHubAdapter",
    "SheetsAdapter",
    "TelegramAdapter",
]
