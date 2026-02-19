# SQLModel Migrations and Database Evolution

This reference covers migration strategies and best practices for evolving SQLModel-based databases.

## Alembic Setup for SQLModel

### Initial Alembic Configuration
```python
# alembic.ini
# This is a basic alembic.ini configuration for SQLModel
[alembic]
# path to migration scripts
script_location = alembic

# template used to generate migration files
# file_template = %%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the python-dateutil library that can be
# installed by adding `alembic[tz]` to the pip requirements
# string value is passed to dateutil.tz.gettz()
# leave blank for localtime
# timezone =

# max length of characters to apply to the
# "slug" field
# max_length = 40

# version_num separator; default is '_' (underscore)
# version_num_sep = .

# version path separator; default is 'os' (path separator)
# version_path_separator = os

# version path map; default is empty.
# Multiple version_path_map keys with the same value can be specified
# version_path_map = my_version_directory:my_version_path, my_version_directory2:my_version_path2

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

[post_write_hooks]
# format using black
hooks = black
black.type = exec
black.executable = black
black.arguments = -l 79 REVISION_SCRIPT_FILENAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### Alembic Environment Configuration
```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Import your SQLModel models
from myapp.models import SQLModel  # Import your models module

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = SQLModel.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
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
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
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
```

### Alembic Script Template
```python
# alembic/script.py.mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

## Migration Patterns and Best Practices

### 1. Basic Migration Pattern
```python
# Example migration file: 001_add_hero_power_level.py
"""Add hero power level

Revision ID: abc123
Revises: def456
Create Date: 2024-01-01 12:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'abc123'
down_revision: Union[str, None] = 'def456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new column
    op.add_column('hero', sa.Column('power_level', sa.Float(), nullable=True))

    # Update existing records
    op.execute("UPDATE hero SET power_level = 50.0 WHERE power_level IS NULL")

    # Make column non-nullable
    op.alter_column('hero', 'power_level', nullable=False)


def downgrade() -> None:
    op.drop_column('hero', 'power_level')
```

### 2. Table Creation Migration
```python
# Example migration file: 002_create_team_table.py
"""Create team table

Revision ID: def456
Revises: None
Create Date: 2024-01-01 11:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'def456'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('team',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('headquarters', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create index
    op.create_index(op.f('ix_team_name'), 'team', ['name'])


def downgrade() -> None:
    op.drop_index(op.f('ix_team_name'), table_name='team')
    op.drop_table('team')
```

### 3. Foreign Key and Relationship Migration
```python
# Example migration file: 003_add_team_to_hero.py
"""Add team to hero relationship

Revision ID: ghi789
Revises: abc123
Create Date: 2024-01-01 13:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'ghi789'
down_revision: Union[str, None] = 'abc123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add foreign key column
    op.add_column('hero', sa.Column('team_id', sa.Integer(), nullable=True))

    # Create foreign key constraint
    op.create_foreign_key(
        'fk_hero_team_id_team',
        'hero', 'team',
        ['team_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_hero_team_id_team', 'hero', type_='foreignkey')
    op.drop_column('hero', 'team_id')
```

## Advanced Migration Scenarios

### Data Migration with Complex Logic
```python
# Example migration file: 004_migrate_hero_categories.py
"""Migrate hero categories to new structure

Revision ID: jkl012
Revises: ghi789
Create Date: 2024-01-01 14:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer


revision: str = 'jkl012'
down_revision: Union[str, None] = 'ghi789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create new category table
    op.create_table('category',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Add category_id to hero table
    op.add_column('hero', sa.Column('category_id', sa.Integer(), nullable=True))

    # Define temporary table for data access
    hero_table = table('hero',
        column('id', Integer),
        column('power_level', sa.Float),
        column('category_id', Integer)
    )

    category_table = table('category',
        column('id', Integer),
        column('name', String)
    )

    # Insert predefined categories
    conn = op.get_bind()
    categories = [
        {'name': 'Super Strength'},
        {'name': 'Flight'},
        {'name': 'Invisibility'},
        {'name': 'Intelligence'}
    ]

    for cat in categories:
        conn.execute(category_table.insert().values(**cat))

    # Map heroes to categories based on power level
    # This is a simplified example - real logic would be more complex
    conn.execute(
        hero_table.update()
        .values(category_id=sa.case(
            (hero_table.c.power_level > 80, 1),  # Super Strength
            (hero_table.c.power_level > 60, 2),  # Flight
            (hero_table.c.power_level > 40, 3),  # Invisibility
            else_=4  # Intelligence
        ))
    )


def downgrade() -> None:
    op.drop_column('hero', 'category_id')
    op.drop_table('category')
```

### Raw SQL for Complex Operations
```python
# Example migration file: 005_optimize_indexes.py
"""Optimize indexes for performance

Revision ID: mno345
Revises: jkl012
Create Date: 2024-01-01 15:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'mno345'
down_revision: Union[str, None] = 'jkl012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old indexes
    op.drop_index('ix_hero_name', table_name='hero')

    # Create new composite index
    op.create_index('ix_hero_name_power', 'hero', ['name', 'power_level'])

    # Create partial index for active heroes
    op.create_index(
        'ix_active_heroes',
        'hero',
        ['id'],
        postgresql_where=sa.text("power_level > 50")
    )


def downgrade() -> None:
    op.drop_index('ix_active_heroes', table_name='hero')
    op.drop_index('ix_hero_name_power', table_name='hero')
    op.create_index('ix_hero_name', 'hero', ['name'])
```

## Migration Management Scripts

### Migration Helper Functions
```python
# migration_helpers.py
import subprocess
import sys
from pathlib import Path
from typing import Optional
import logging

class MigrationManager:
    def __init__(self, alembic_ini_path: str = "alembic.ini"):
        self.alembic_ini_path = alembic_ini_path
        self.logger = logging.getLogger(__name__)

    def init_alembic(self, database_url: str, target_dir: str = "alembic"):
        """Initialize Alembic in the project"""
        try:
            subprocess.run([
                sys.executable, "-m", "alembic", "init",
                "-t", "generic", target_dir
            ], check=True)
            self.logger.info(f"Alembic initialized in {target_dir}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to initialize Alembic: {e}")
            raise

    def generate_migration(self, message: str, autogenerate: bool = True) -> Optional[str]:
        """Generate a new migration file"""
        cmd = [
            sys.executable, "-m", "alembic", "revision",
            "-m", message
        ]

        if autogenerate:
            cmd.insert(2, "--autogenerate")

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            # Extract migration file path from output
            output = result.stdout
            for line in output.split('\n'):
                if 'Generating' in line and '->' in line:
                    return line.split()[-1]  # Return the file path
            return None
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to generate migration: {e}")
            self.logger.error(e.stderr)
            return None

    def run_migrations(self, revision: str = "head"):
        """Run migrations to a specific revision"""
        try:
            subprocess.run([
                sys.executable, "-m", "alembic", "upgrade", revision
            ], check=True)
            self.logger.info(f"Migrations applied up to {revision}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to run migrations: {e}")
            raise

    def check_pending_migrations(self) -> bool:
        """Check if there are pending migrations"""
        try:
            result = subprocess.run([
                sys.executable, "-m", "alembic", "current"
            ], capture_output=True, text=True, check=True)

            # If output contains "(head)", there are no pending migrations
            return "(head)" not in result.stdout
        except subprocess.CalledProcessError:
            # If command fails, assume there are pending migrations
            return True

    def create_initial_migration(self, message: str = "Initial migration"):
        """Create the initial migration based on current models"""
        # First, make sure we have an alembic directory
        if not Path("alembic").exists():
            self.init_alembic("")

        return self.generate_migration(message, autogenerate=True)
```

### Automated Migration Workflow
```python
# migration_workflow.py
from migration_helpers import MigrationManager
from sqlmodel import SQLModel
import importlib
import sys
from typing import List

class AutomatedMigrationWorkflow:
    def __init__(self, database_url: str, models_module_path: str):
        self.database_url = database_url
        self.models_module_path = models_module_path
        self.migration_manager = MigrationManager()

    def setup_migration_environment(self):
        """Setup the migration environment"""
        # Import models to register them with SQLModel metadata
        importlib.import_module(self.models_module_path)

        # Update alembic.ini with database URL if needed
        self._update_alembic_config()

    def _update_alembic_config(self):
        """Update alembic.ini with the database URL"""
        alembic_ini_path = Path("alembic.ini")

        if alembic_ini_path.exists():
            content = alembic_ini_path.read_text()
            if "sqlalchemy.url =" not in content:
                # Add the database URL to the config
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() == "[alembic]":
                        lines.insert(i + 1, f"sqlalchemy.url = {self.database_url}")
                        break
                alembic_ini_path.write_text('\n'.join(lines))

    def generate_and_apply_migrations(self, message: str) -> bool:
        """Generate and apply migrations in one step"""
        try:
            # Generate migration
            migration_file = self.migration_manager.generate_migration(message)
            if not migration_file:
                print("No changes detected or migration generation failed")
                return False

            print(f"Generated migration: {migration_file}")

            # Apply migration
            self.migration_manager.run_migrations()
            print("Migrations applied successfully")
            return True

        except Exception as e:
            print(f"Error during migration: {e}")
            return False

    def ensure_database_schema(self) -> bool:
        """Ensure the database schema matches the models"""
        try:
            # Check if there are pending migrations
            has_pending = self.migration_manager.check_pending_migrations()

            if has_pending:
                print("Applying pending migrations...")
                self.migration_manager.run_migrations()
            else:
                print("Database schema is up to date")

            return True
        except Exception as e:
            print(f"Error ensuring database schema: {e}")
            return False
```

## Migration Testing

### Migration Testing Framework
```python
# test_migrations.py
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session
from alembic.command import upgrade, downgrade
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
import tempfile
import os

class MigrationTester:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.alembic_cfg = Config("alembic.ini")
        self.script_dir = ScriptDirectory.from_config(self.alembic_cfg)

    def test_migration_up_down(self, migration_rev: str):
        """Test that a migration can go up and down successfully"""
        # Create a temporary database for testing
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_db_url = f"sqlite:///{tmp.name}"

        try:
            # Upgrade to the migration
            self.alembic_cfg.set_main_option("sqlalchemy.url", temp_db_url)
            upgrade(self.alembic_cfg, migration_rev)

            # Verify the migration worked by checking if expected tables exist
            engine = create_engine(temp_db_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
                tables = [row[0] for row in result]

                # Here you'd add specific checks based on your migration
                # For example, if your migration creates a 'users' table:
                # assert 'users' in tables

            # Downgrade from the migration
            downgrade(self.alembic_cfg, "base")

            # Verify tables were removed (or changed as expected)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
                tables_after = [row[0] for row in result]

                # Add specific checks for downgrade
                # assert 'users' not in tables_after

        finally:
            # Clean up temporary database
            os.unlink(tmp.name)

    def test_data_migration(self):
        """Test that data migrations work correctly"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            temp_db_url = f"sqlite:///{tmp.name}"

        try:
            self.alembic_cfg.set_main_option("sqlalchemy.url", temp_db_url)

            # Set up initial state
            engine = create_engine(temp_db_url)
            SQLModel.metadata.create_all(engine)

            # Insert test data that will be affected by migration
            with Session(engine) as session:
                # Add test data here
                pass

            # Run the migration
            upgrade(self.alembic_cfg, "head")

            # Verify data was migrated correctly
            with Session(engine) as session:
                # Check that data was transformed as expected
                pass

        finally:
            os.unlink(tmp.name)

# Example test using pytest
def test_all_migrations():
    """Test that all migrations can be applied in sequence"""
    tester = MigrationTester("sqlite:///test.db")

    # Get all migration versions
    revisions = []
    for script in tester.script_dir.walk_revisions():
        revisions.append(script.revision)

    # Apply migrations in order
    for rev in reversed(revisions):
        tester.test_migration_up_down(rev)
```

## Production Migration Strategies

### Zero-Downtime Migration Pattern
```python
# production_migrations.py
from sqlalchemy import text
from typing import Callable, Any
import logging

class ProductionMigrationManager:
    def __init__(self, session):
        self.session = session
        self.logger = logging.getLogger(__name__)

    def safe_column_addition(self, table_name: str, column_name: str,
                           column_type: str, default_value: Any = None):
        """Safely add a column with minimal impact"""
        # Step 1: Add column as nullable
        alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        self.session.execute(text(alter_sql))

        # Step 2: Populate existing records (do this in batches for large tables)
        if default_value is not None:
            update_sql = f"UPDATE {table_name} SET {column_name} = :value WHERE {column_name} IS NULL"
            self.session.execute(text(update_sql), {"value": default_value})

        # Step 3: Make column non-nullable (if needed) and add constraints
        # This step might require application coordination in production
        self.session.commit()

    def safe_table_rename(self, old_name: str, new_name: str):
        """Safely rename a table with application coordination"""
        # Step 1: Create new table with new structure
        # (Implementation depends on specific requirements)

        # Step 2: Copy data in batches
        # (Implementation depends on specific requirements)

        # Step 3: Switch application to use new table
        # (Requires application-level coordination)

        # Step 4: Drop old table
        # (After verifying everything works)

    def run_migration_with_validation(self, migration_func: Callable,
                                    validation_func: Callable) -> bool:
        """Run a migration with pre and post validation"""
        try:
            # Pre-migration validation
            if not validation_func("before"):
                self.logger.error("Pre-migration validation failed")
                return False

            # Run migration
            migration_func()

            # Post-migration validation
            if not validation_func("after"):
                self.logger.error("Post-migration validation failed")
                # Consider rolling back here
                return False

            self.logger.info("Migration completed successfully with validation")
            return True

        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            return False
```

## Complete Migration Example

```python
# complete_migration_example.py
from sqlmodel import SQLModel, Field, create_engine
from typing import Optional
from alembic.config import Config
from alembic import command
import os

# Example models
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    email: str
    is_active: bool = Field(default=True)

class Post(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    author_id: int = Field(foreign_key="user.id")
    is_published: bool = Field(default=False)

def setup_database_with_migrations():
    """Complete example of setting up database with migrations"""
    database_url = "sqlite:///example.db"

    # Create engine
    engine = create_engine(database_url)

    # Create tables directly (for development)
    # In production, you'd use Alembic migrations
    SQLModel.metadata.create_all(engine)

    # For Alembic setup, you would:
    # 1. Initialize Alembic: alembic init alembic
    # 2. Configure alembic/env.py to use SQLModel.metadata
    # 3. Generate initial migration: alembic revision --autogenerate -m "Initial migration"
    # 4. Apply migration: alembic upgrade head

    return engine

def create_alembic_migration():
    """Create an example Alembic migration"""
    # Create alembic directory if it doesn't exist
    if not os.path.exists("alembic"):
        os.makedirs("alembic")

    # Create env.py
    env_content = '''from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from myapp.models import SQLModel  # Adjust import path

config = context.config

if config.config_file_name is not None:
    from logging.config import fileConfig
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata

def run_migrations_offline() -> None:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
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
'''

    with open("alembic/env.py", "w") as f:
        f.write(env_content)

if __name__ == "__main__":
    engine = setup_database_with_migrations()
    print("Database setup completed!")
```