from logshift.core.adapter import TransportAdapter
from logshift.core.manager import LogManager
from logshift.core.fetcher import LogFetcher
from logshift.core.exceptions import LogshiftError, ConfigurationError, AdapterError
from logshift.adapters.github import GitHubAdapter
from logshift.adapters.sheets import SheetsAdapter
from logshift.adapters.telegram import TelegramAdapter
from logshift.adapters.discord import DiscordAdapter
from logshift.adapters.slack import SlackAdapter

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
    "DiscordAdapter",
    "SlackAdapter",
]
