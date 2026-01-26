import re
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Regex для валидации формата Telegram bot token
# Формат: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz (8-10 цифр : 35 символов base64)
BOT_TOKEN_PATTERN = re.compile(r"^\d{8,10}:[A-Za-z0-9_-]{35}$")


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Обязательные
    bot_token: str = Field(..., min_length=1)
    admin_id: int = Field(..., gt=0)
    payment_link: str = Field(..., min_length=1)

    # База данных
    database_url: str = "sqlite+aiosqlite:///pause.db"

    # Продукт
    product_name: str = "Пауза"
    product_price: int = Field(default=79, gt=0)
    product_currency: str = "EUR"

    # Notion (опциональные)
    notion_token: str = ""
    notion_content_db: str = ""
    notion_ui_texts_db: str = ""

    # Медиа
    welcome_photo_id: str = ""

    @field_validator("bot_token")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        if not v or v == "":
            raise ValueError("BOT_TOKEN is required")
        if not BOT_TOKEN_PATTERN.match(v):
            raise ValueError(
                "BOT_TOKEN format invalid. "
                "Expected format: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz "
                "(8-10 digits, colon, 35 alphanumeric characters)"
            )
        return v

    @field_validator("payment_link")
    @classmethod
    def validate_payment_link(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("PAYMENT_LINK must be a valid URL")
        return v


def load_config() -> Config:
    return Config()
