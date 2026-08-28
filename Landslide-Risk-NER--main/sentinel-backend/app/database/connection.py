import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# Find .env from the main sentinel-backend folder
env_file = Path(__file__).resolve().parents[2] / ".env"

# Load settings from .env
load_dotenv(dotenv_path=env_file)


use_sqlite = os.getenv("USE_SQLITE", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


db_host = os.getenv("DB_HOST", "127.0.0.1")
db_port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")


if use_sqlite or not (db_name and db_user and db_password):
    project_root = Path(__file__).resolve().parents[2]
    database_url = f"sqlite:///{project_root / 'sentinel.db'}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
else:
    # Create the PostgreSQL connection safely
    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=db_user,
        password=db_password,
        host=db_host,
        port=int(db_port),
        database=db_name,
    )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


class Base(DeclarativeBase):
    pass


def get_database():
    database = SessionLocal()

    try:
        yield database
    finally:
        database.close()