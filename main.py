import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from config import load_config
from database import init_db, close_db
from handlers import (
    onboarding_router,
    pause_router,
    box_router,
    orders_router,
    admin_router,
    menu_router,
)
from scheduler import create_scheduler
from content import ContentManager


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

    # Загружаем кэш контента из SQLite
    content_manager = ContentManager.get_instance()
    try:
        await content_manager.reload()
        logging.info("Кэш контента загружен")
    except Exception as e:
        logging.warning(f"Не удалось загрузить кэш контента: {e}, используется fallback")

    # Создаём бота и диспетчер
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Передаём config во все хэндлеры
    dp["config"] = config

    # Регистрируем роутеры (порядок важен — menu первым для команд)
    dp.include_router(menu_router)
    dp.include_router(onboarding_router)
    dp.include_router(pause_router)
    dp.include_router(box_router)
    dp.include_router(orders_router)
    dp.include_router(admin_router)

    # Устанавливаем команды бота (кнопка Menu)
    await bot.set_my_commands([
        BotCommand(command="pause", description="Пауза"),
        BotCommand(command="breathe", description="Подышать"),
        BotCommand(command="movie", description="Кино"),
        BotCommand(command="book", description="Книга"),
        BotCommand(command="box", description="Новый набор"),
        BotCommand(command="settings", description="Настроить паузу"),
    ])

    # Создаём и запускаем планировщик напоминаний
    pause_scheduler = create_scheduler(bot)
    pause_scheduler.start()

    # Запускаем
    logging.info("Бот запущен")

    try:
        await dp.start_polling(bot)
    finally:
        # Cleanup
        pause_scheduler.stop()
        await close_db()
        logging.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
