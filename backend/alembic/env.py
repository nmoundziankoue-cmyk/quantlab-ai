import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Make the backend directory importable so our modules resolve correctly
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings  # noqa: E402
from models.base import Base  # noqa: E402
import models.portfolio  # noqa: F401  — registers ORM models with Base.metadata
import models.watchlist  # noqa: F401
import models.research   # noqa: F401
import models.analytics  # noqa: F401
import models.trading    # noqa: F401
import models.research_workspace   # noqa: F401
import models.document_intelligence  # noqa: F401
import models.alternative_data       # noqa: F401
import models.screener               # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the database URL from our settings (honours .env overrides)
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
