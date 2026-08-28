import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import URL
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from app.database.connection import Base

# IMPORTANT:
# Import the model module so SQLAlchemy registers
# predictions, alerts, and community_reports
# into Base.metadata.
from app.database import models  # noqa: F401


# =========================================================
# PROJECT / ENVIRONMENT SETUP
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(
    PROJECT_ROOT / ".env"
)


# =========================================================
# ALEMBIC CONFIGURATION
# =========================================================

config = context.config


if config.config_file_name is not None:
    fileConfig(
        config.config_file_name
    )


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

DB_HOST = os.getenv(
    "DB_HOST",
    "127.0.0.1",
)

DB_PORT = os.getenv(
    "DB_PORT",
    "5432",
)

DB_NAME = os.getenv(
    "DB_NAME",
    "sentinel_ner",
)

DB_USER = os.getenv(
    "DB_USER",
    "sentinel_app",
)

DB_PASSWORD = os.getenv(
    "DB_PASSWORD"
)


if not DB_PASSWORD:
    raise RuntimeError(
        "DB_PASSWORD is missing from the .env file."
    )


database_url = URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
)


database_url_string = (
    database_url
    .render_as_string(
        hide_password=False
    )
    .replace("%", "%%")
)


config.set_main_option(
    "sqlalchemy.url",
    database_url_string,
)


# =========================================================
# SQLALCHEMY MODEL METADATA
# =========================================================

target_metadata = Base.metadata


# =========================================================
# OFFLINE MIGRATIONS
# =========================================================

def run_migrations_offline() -> None:
    """
    Run migrations without opening
    a live database connection.
    """

    url = config.get_main_option(
        "sqlalchemy.url"
    )

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# =========================================================
# ONLINE MIGRATIONS
# =========================================================

def run_migrations_online() -> None:
    """
    Run migrations using the real
    PostgreSQL database connection.
    """

    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section,
            {},
        ),
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


# =========================================================
# RUN MIGRATIONS
# =========================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()