from logshift.core.adapter import TransportAdapter
from logshift.core.manager import LogManager
from logshift.core.exceptions import LogshiftError, ConfigurationError, AdapterError
from logshift.adapters.github import GitHubAdapter

__version__ = "0.1.0"
__all__ = [
    "TransportAdapter",
    "LogManager",
    "LogshiftError",
    "ConfigurationError",
    "AdapterError",
    "GitHubAdapter",
]
