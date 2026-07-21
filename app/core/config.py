"""
app/core/config.py
------------------
Central configuration using pydantic-settings.
All env vars are validated at startup — the app refuses to start
if required values are missing.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_name: str = "BizPilot NG"
    app_env: str = "development"
    app_port: int = 8000
    app_host: str = "0.0.0.0"
    secret_key: str = Field(..., min_length=32)
    debug: bool = True

    # --- Telegram ---
    telegram_bot_token: str = Field(...)
    telegram_webhook_secret: str = Field(...)
    webhook_base_url: str = Field(...)

    # --- Anthropic ---
    anthropic_api_key: str = Field(...)
    anthropic_base_url: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 2000

    # --- OpenAI (Whisper) ---
    openai_api_key: str = ""

    # --- Supabase ---
    supabase_url: str = Field(...)
    supabase_anon_key: str = Field(...)
    supabase_service_key: str = Field(...)
    supabase_bucket_name: str = "bizpilot-documents"

    # --- Paystack ---
    paystack_secret_key: str = Field(...)
    paystack_public_key: str = Field(...)
    paystack_webhook_secret: str = ""
    paystack_pro_plan_code: str = ""
    paystack_commander_plan_code: str = ""

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Email ---
    resend_api_key: str = ""
    email_from: str = "noreply@bizpilot.ng"
    email_from_name: str = "BizPilot NG"

    # --- Subscription limits ---
    free_monthly_limit: int = 5
    pro_monthly_limit: int = 999999
    commander_monthly_limit: int = 999999

    # --- Pricing (kobo) ---
    pro_price_kobo: int = 499900       # ₦4,999
    commander_price_kobo: int = 1299900  # ₦12,999

    @property
    def webhook_url(self) -> str:
        """Full Telegram webhook endpoint URL."""
        return f"{self.webhook_base_url}/webhook/telegram/{self.telegram_webhook_secret}"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def paystack_base_url(self) -> str:
        return "https://api.paystack.co"


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance.
    Import and call this anywhere:
        from app.core.config import get_settings
        settings = get_settings()
    """
    return Settings()


# Convenience alias
settings = get_settings()
