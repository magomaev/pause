import asyncio
import logging
import signal
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
from middleware import ThrottlingMiddleware


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

    # Подключаем middleware
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())

    # Регистрируем роутеры (порядок важен!)
    # 1. Команды и FSM — сначала, чтобы они имели приоритет
    dp.include_router(onboarding_router)  # /start, /help, онбординг FSM
    dp.include_router(pause_router)       # /pause
    dp.include_router(box_router)         # предзаказ набора FSM
    dp.include_router(orders_router)      # заказы FSM
    dp.include_router(admin_router)       # админ команды
    # 2. Menu последним — содержит catch-all для reply keyboard
    dp.include_router(menu_router)

    # Устанавливаем команды бота (кнопка Menu)
    await bot.set_my_commands([
        BotCommand(command="pause", description="Пауза"),
        BotCommand(command="breathe", description="Подышать"),
        BotCommand(command="movie", description="Кино"),
        BotCommand(command="book", description="Книга"),
        BotCommand(command="box", description="Новый набор"),
        BotCommand(command="settings", description="Настроить паузу"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="cancel", description="Отменить действие"),
    ])

    # Создаём и запускаем планировщик напоминаний
    pause_scheduler = create_scheduler(bot)
    pause_scheduler.start()

    # Обработка сигналов для graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler():
        logging.info("Получен сигнал завершения, останавливаем...")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows не поддерживает add_signal_handler
            pass

    # Запускаем
    logging.info("Бот запущен")

    async def shutdown():
        """Graceful shutdown."""
        await shutdown_event.wait()
        logging.info("Начинаем graceful shutdown...")

        # Останавливаем polling
        await dp.stop_polling()

    try:
        # Запускаем polling и ждём сигнала завершения
        await asyncio.gather(
            dp.start_polling(bot),
            shutdown(),
            return_exceptions=True
        )
    finally:
        # Cleanup
        logging.info("Останавливаем планировщик...")
        pause_scheduler.stop()
        logging.info("Закрываем соединение с БД...")
        await close_db()
        logging.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
