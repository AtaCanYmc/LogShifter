class LogportError(Exception):
    """Base exception for all logport related errors."""
    pass


class ConfigurationError(LogportError):
    """Raised when there is a configuration-related error (e.g. missing environment variables)."""
    pass


class AdapterError(LogportError):
    """Raised when a TransportAdapter fails to ship/archive logs."""
    pass
