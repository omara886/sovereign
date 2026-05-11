from collections.abc import AsyncGenerator
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()
engine = None
SessionLocal = None

try:
    engine = create_async_engine(settings.DATABASE_URL, future=True, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
except ModuleNotFoundError as exc:
    if "asyncpg" not in str(exc):
        raise
    logger.warning("asyncpg is not installed; database engine is disabled for import-only mode")


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if SessionLocal is None:
        raise RuntimeError("Database engine is not available in this environment")
    async with SessionLocal() as session:
        yield session
