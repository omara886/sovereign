from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    ANTHROPIC_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""   # api.deepseek.com — 10x cheaper than Sonnet
    FAL_KEY: str = ""

    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "sovereign-assets"
    R2_PUBLIC_URL: str = ""

    RESEND_API_KEY: str = ""
    FOUNDER_EMAIL: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    LINKEDIN_ACCESS_TOKEN: str = ""
    LINKEDIN_ORG_ID: str = ""
    INSTAGRAM_ACCESS_TOKEN: str = ""
    INSTAGRAM_USER_ID: str = ""
    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    TWITTER_ACCESS_TOKEN: str = ""
    TWITTER_ACCESS_SECRET: str = ""
    GOOGLE_ADS_DEVELOPER_TOKEN: str = ""
    GOOGLE_ADS_CUSTOMER_ID: str = ""
    GOOGLE_ADS_REFRESH_TOKEN: str = ""
    GOOGLE_ANALYTICS_PROPERTY_ID: str = ""

    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"
    API_SECRET_KEY: str = ""
    RESEND_FROM_EMAIL: str = "sovereign@notifications.ai"
    # Self-referential public URL — used for file serve links stored in DB
    BACKEND_PUBLIC_URL: str = "https://backend-production-37a17.up.railway.app"


@lru_cache
def get_settings() -> Settings:
    return Settings()
