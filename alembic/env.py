import asyncio
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context

from models import Base

config = context.config
fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", "sqlite:///:memory:")

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(lambda conn: context.configure(connection=conn, target_metadata=target_metadata))

        async with connection.begin():
            await connection.run_sync(lambda conn: context.configure(connection=conn, target_metadata=target_metadata))


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
