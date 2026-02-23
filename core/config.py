from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Bot
    bot_token: str
    bot_mode: str = "polling"  # webhook | polling

    # Webhook (required when bot_mode=webhook)
    webhook_base_url: str = ""
    webhook_path: str = "/webhook/bot"
    webhook_secret: str = ""

    # Channel
    channel_id: int = 0

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/tgbot"

    # Admin
    admin_username: str = "admin"
    admin_password_hash: str = ""
    secret_key: str = "change_me_to_random_32_chars_string"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    @property
    def webhook_url(self) -> str:
        return f"{self.webhook_base_url}{self.webhook_path}"


settings = Settings()
