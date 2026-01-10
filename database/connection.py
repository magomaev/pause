from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database.models import Base
import os

engine = None
async_session = None


async def init_db(database_url: str = None):
    global engine, async_session
    
    # Всегда используем SQLite
    database_url = "sqlite+aiosqlite:///bot.db"
    
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session() -> AsyncSession:
    return async_session()
