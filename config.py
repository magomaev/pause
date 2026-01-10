import os
from dataclasses import dataclass


@dataclass
class Config:
    bot_token: str
    admin_id: int
    database_url: str
    payment_link: str  # Revolut Payment Link
    
    # Продукт
    product_name: str = "Пауза"
    product_price: int = 79
    product_currency: str = "EUR"


def load_config() -> Config:
    return Config(
        bot_token=os.getenv("BOT_TOKEN", ""),
        admin_id=int(os.getenv("ADMIN_ID", "0")),
        database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot.db"),
        payment_link=os.getenv("PAYMENT_LINK", ""),
    )
