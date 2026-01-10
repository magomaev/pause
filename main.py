import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import load_config
from database import init_db
from handlers import base_router, orders_router, admin_router


async def main():
    # Логирование
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Загружаем конфиг
    config = load_config()
    
    if not config.bot_token:
        raise ValueError("BOT_TOKEN не установлен")
    
    # Инициализируем базу данных
    await init_db(config.database_url)
    
    # Создаём бота и диспетчер
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Передаём config во все хэндлеры
    dp["config"] = config
    
    # Регистрируем роутеры
    dp.include_router(base_router)
    dp.include_router(orders_router)
    dp.include_router(admin_router)
    
    # Запускаем
    logging.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
