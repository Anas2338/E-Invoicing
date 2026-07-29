from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import ALL models here to register them with Alembic
from src.models.base import Base
from src.models.invoice import Invoice  # noqa
from src.models.user import User  # noqa
from src.models.fbr_response import FBRResponse  # noqa
from src.models.user_saved_product import UserSavedProduct  # noqa
from src.models.idempotency import IdempotencyCache  # noqa
from src.models.posting_log import PostingLog  # noqa
from src.models.daily_posting_counter import DailyPostingCounter  # noqa

# Import excel staging models
from src.models.excel_staging import ExcelStagingSession, ExcelStagingRow  # noqa

# Import FBR master data models
from src.models.fbr_master_data import (
    FBRBase,
    FBRProvince,
    FBRUOM,
    FBRHSCode,
    FBRTransactionType,
    FBRInvoiceType,
    FBRSROItem,
    FBRSyncLog
)  # noqa

from src.config.settings import settings

# Combine metadata from Base, FBRBase, and SQLModel for main database
from sqlalchemy import MetaData
from sqlmodel import SQLModel
combined_metadata = MetaData()

# Merge tables from Base and FBRBase only (main database tables)
for table in Base.metadata.tables.values():
    table.to_metadata(combined_metadata)
for table in FBRBase.metadata.tables.values():
    table.to_metadata(combined_metadata)
for table in SQLModel.metadata.tables.values():
    table.to_metadata(combined_metadata)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option('sqlalchemy.url', settings.database_url)
target_metadata = combined_metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
