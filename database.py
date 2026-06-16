import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_raw_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://myappuser:your_strong_password@localhost/eaglepurse")

# Render (and many hosts) provide postgres:// or postgresql:// — normalize to asyncpg
DATABASE_URL = (
    _raw_url
    .replace("postgres://", "postgresql+asyncpg://")
    .replace("postgresql://", "postgresql+asyncpg://")
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
