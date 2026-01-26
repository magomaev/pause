import logging
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database.models import Base

logger = logging.getLogger(__name__)


def _sanitize_db_url_for_log(url: str) -> str:
    """Безопасно извлечь хост из URL для логирования (без credentials)."""
    try:
        parsed = urlparse(url)
        if parsed.hostname:
            return f"{parsed.scheme}://***@{parsed.hostname}{parsed.path or ''}"
        return url.split("://")[0] + "://***"
    except Exception:
        return "***"

engine = None
async_session = None


async def init_db(database_url: str | None = None):
    """Инициализация базы данных."""
    global engine, async_session

    # Если URL не передан, используем SQLite
    if not database_url:
        database_url = "sqlite+aiosqlite:///bot.db"

    # Преобразование URL для async драйверов
    if database_url.startswith("sqlite://") and "+aiosqlite" not in database_url:
        database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://")
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://")
    elif database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    # Настройки пула зависят от типа БД
    is_sqlite = "sqlite" in database_url
    engine_kwargs = {
        "echo": False,
    }

    if is_sqlite:
        # SQLite использует NullPool, настраиваем только connect_args
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # PostgreSQL: полная конфигурация пула соединений
        engine_kwargs.update({
            "pool_pre_ping": True,      # Проверка соединения перед использованием
            "pool_size": 5,             # Базовый размер пула
            "max_overflow": 10,         # Дополнительные соединения при пике
            "pool_recycle": 1800,       # Переподключение каждые 30 минут
            "pool_timeout": 30,         # Таймаут ожидания соединения из пула
        })

    engine = create_async_engine(database_url, **engine_kwargs)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info(f"Database initialized: {_sanitize_db_url_for_log(database_url)}")


async def close_db():
    """Закрытие соединений с базой данных."""
    global engine, async_session

    if engine:
        await engine.dispose()
        logger.info("Database connections closed")

    engine = None
    async_session = None


@asynccontextmanager
async def get_session() -> AsyncSession:
    """Контекстный менеджер для получения сессии."""
    if async_session is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    session = async_session()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
