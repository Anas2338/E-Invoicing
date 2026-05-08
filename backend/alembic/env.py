from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import ALL models here to register them with Alembic
from src.models.base import Base
from src.models.invoice import Invoice  # noqa
from src.models.user import User  # noqa
from src.models.fbr_response import FBRResponse  # noqa
from src.models.audit_log import AuditLog  # noqa
from src.models.posting_log import PostingLog  # noqa
from src.models.daily_posting_counter import DailyPostingCounter  # noqa
from src.models.user_saved_product import UserSavedProduct  # noqa
from src.models.user_saved_buyer import UserSavedBuyer  # noqa
from src.models.user_saved_hs_code import UserSavedHSCode  # noqa
from src.models.user_saved_product_description import UserSavedProductDescription  # noqa
from src.models.user_saved_tax_rate import UserSavedTaxRate  # noqa
from src.models.user_saved_uom import UserSavedUOM  # noqa
from src.models.idempotency import IdempotencyCache  # noqa

# Import automation models (for automation database)
from src.models.automation_invoice import AutomationInvoice  # noqa
from src.models.automation_log import AutomationLog  # noqa
from src.models.excel_upload_session import ExcelUploadSession  # noqa
from src.models.transfer_log import TransferLog  # noqa
from src.models.ai_agent_health_check import AIAgentHealthCheck  # noqa

from src.config.settings import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Determine which database we're migrating based on config file
is_automation_db = config.config_file_name and 'alembic_automation.ini' in config.config_file_name

# Set the database URL from settings
if is_automation_db:
    config.set_main_option('sqlalchemy.url', settings.automation_database_url)
    # For automation database, use only automation models' metadata
    # We'll use Base.metadata but only automation tables will be created
    target_metadata = Base.metadata
else:
    config.set_main_option('sqlalchemy.url', settings.database_url)
    # For main database, use all models' metadata
    target_metadata = Base.metadata


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
