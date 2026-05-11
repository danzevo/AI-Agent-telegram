from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    telegram_bot_token: str
    lm_studio_url: str = "http://localhost:1234/v1"

    # "polling" or "webhook"
    bot_mode: str = "polling"
    webhook_url: str | None = None
    ssl_verify: bool = True
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()