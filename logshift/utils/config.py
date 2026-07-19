import os
from pathlib import Path
from typing import Dict, Optional
from logshift.core.exceptions import ConfigurationError


def load_env(env_path: Optional[str] = None) -> Dict[str, str]:
    """
    Manually loads .env file into os.environ.
    This avoids mandatory external dependencies like python-dotenv.
    """
    path = Path(env_path) if env_path else Path(".env")
    if not path.exists():
        return dict(os.environ)

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                os.environ.setdefault(key, val)
                
    return dict(os.environ)


def get_required_env(key: str) -> str:
    """Gets an environment variable or raises a ConfigurationError if missing."""
    val = os.environ.get(key)
    if not val:
        raise ConfigurationError(f"Missing required environment variable: {key}")
    return val
