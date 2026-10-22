"""Application configuration module using pydantic-settings."""

from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configuration settings loaded from environment variables and .env file."""

    # Telegram Bot
    BOT_TOKEN: str = Field(default="", description="Telegram Bot token from @BotFather")
    ADMIN_TELEGRAM_ID: int = Field(default=0, description="Telegram User ID of Owner/Superadmin")

    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./bot_database.db",
        description="Async SQLAlchemy database connection string",
    )
    DATABASE_ECHO: bool = Field(default=False, description="SQLAlchemy query echoing")

    # Redis (Optional)
    REDIS_URL: Optional[str] = Field(default=None, description="Redis URL for caching / FSM storage")

    # AI Assistant (OpenAI)
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="OpenAI model name")

    # Webhook vs Polling
    USE_WEBHOOK: bool = Field(default=False, description="Run in webhook mode with FastAPI")
    WEBHOOK_URL: Optional[str] = Field(default=None, description="Public HTTPS URL for webhook")
    WEBHOOK_PATH: str = Field(default="/webhook", description="Path for incoming webhook updates")
    WEBHOOK_SECRET: Optional[str] = Field(default=None, description="Secret token for Telegram webhook validation")
    SERVER_HOST: str = Field(default="0.0.0.0", description="FastAPI host")
    SERVER_PORT: int = Field(default=8000, description="FastAPI port")

    # Business OS Defaults
    TIMEZONE: str = Field(default="Asia/Phnom_Penh", description="Default operational timezone")
    CURRENCY_SYMBOL: str = Field(default="$", description="Currency symbol displayed across the app")
    LOW_STOCK_THRESHOLD: int = Field(default=10, description="Default threshold for low stock alert")
    MORNING_REMINDER_TIME: str = Field(default="08:00", description="HH:MM for morning reminder")
    DAILY_REPORT_REMINDER_TIME: str = Field(default="18:00", description="HH:MM for report reminder")
    RATE_LIMIT_PER_SECOND: float = Field(default=2.0, description="Max messages per second per user")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Storage paths
    EXPORTS_DIR: Path = Field(default=BASE_DIR / "exports", description="Directory for exported CSV/Excel files")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
