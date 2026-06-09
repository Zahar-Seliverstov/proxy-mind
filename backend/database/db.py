from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.models import Base

_DB_PATH = Path.home() / ".config" / "proxymind" / "proxymind.db"

_engine = create_async_engine(
    f"sqlite+aiosqlite:///{_DB_PATH}",
    connect_args={"check_same_thread": False},
)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    _engine, expire_on_commit=False
)


async def init_db() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
