import re
import sys
import traceback
from typing import Any


class LogshiftError(Exception):
    """Base exception for all logshift related errors."""

    pass


class ConfigurationError(LogshiftError):
    """Raised when there is a configuration-related error."""

    pass


class AdapterError(LogshiftError):
    """Raised when a TransportAdapter fails to ship/archive logs."""

    pass


def sanitize_exception(exctype: type, value: BaseException, tb: Any) -> None:
    """
    Custom sys.excepthook to intercept tracebacks and replace sensitive credentials
    like keys, tokens, webhooks, and secrets with masked placeholders.
    """
    tb_lines = traceback.format_exception(exctype, value, tb)
    sanitized = []
    for line in tb_lines:
        # Mask Discord & Slack webhook urls
        line = re.sub(
            r"https://(discord\.com/api/webhooks/|hooks\.slack\.com/services/)\S+",
            r"https://\1[MASKED]",
            line,
        )
        # Mask GitHub tokens
        line = re.sub(r"ghp_\w+", "ghp_[MASKED]", line)
        # Mask Telegram bot tokens
        line = re.sub(r"bot\d+:\w+", "bot[MASKED]", line)
        sanitized.append(line)
    sys.__stderr__.write("".join(sanitized))


# Register exception hook globally
sys.excepthook = sanitize_exception
