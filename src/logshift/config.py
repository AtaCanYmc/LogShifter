from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogshiftSettings(BaseSettings):
    """
    Logshift settings configuration class powered by pydantic-settings.
    """
    # Supabase Configuration
    supabase_url: str
    supabase_key: str
    supabase_table_name: str = "logs"
    supabase_date_column: str = "created_at"

    # GitHub Configuration
    logshift_github_token: Optional[str] = None
    logshift_github_repo: Optional[str] = None
    logshift_github_path: str = "logs/archive.json"
    logshift_github_branch: str = "main"

    # Google Sheets Configuration
    google_service_account_file: Optional[str] = None
    google_spreadsheet_id: Optional[str] = None
    google_worksheet_name: str = "Logs"

    # Telegram Configuration
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # Settings config to allow loading from env/file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
