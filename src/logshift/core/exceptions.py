class LogshiftError(Exception):
    """Base exception for all logshift related errors."""

    pass


class ConfigurationError(LogshiftError):
    """Raised when there is a configuration-related error."""

    pass


class AdapterError(LogshiftError):
    """Raised when a TransportAdapter fails to ship/archive logs."""

    pass
