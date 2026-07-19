from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogshiftSettings(BaseSettings):
    """
    Logshift settings configuration class powered by pydantic-settings.
    Automatically reads environment variables and optionally parses a .env file.
    """
    # Supabase Configuration
    supabase_url: str
    supabase_key: str
    supabase_table_name: str = "logs"
    supabase_date_column: str = "created_at"

    # GitHub Configuration
    logshift_github_token: str
    logshift_github_repo: str
    logshift_github_path: str = "logs/archive.json"
    logshift_github_branch: str = "main"

    # Settings config to allow loading from .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
