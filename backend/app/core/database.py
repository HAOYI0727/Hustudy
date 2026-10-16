from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker
from .config import get_settings


def _engine():
    settings = get_settings()
    if settings.database_url.startswith("sqlite:///"):
        Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(
            parents=True, exist_ok=True
        )
    engine = create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    return engine


engine = _engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    tables = inspect(engine).get_table_names()
    with engine.connect() as connection:
        revision = (
            connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar()
            if "alembic_version" in tables
            else None
        )
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    if revision == ScriptDirectory.from_config(config).get_current_head():
        return
    # SQLite online backup includes WAL; migration never copies a live .db blindly.
    if tables and engine.url.database and engine.url.database != ":memory:":
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        backup_path = Path(engine.url.database + f".pre-migration-{stamp}.bak")
        with (
            sqlite3.connect(engine.url.database) as source,
            sqlite3.connect(backup_path) as target,
        ):
            source.backup(target)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as db:
        yield db


def begin_read_snapshot(db: Session) -> None:
    """sqlite3 legacy mode does not BEGIN for SELECT; make count/page atomic."""
    connection = db.connection()
    if (
        connection.dialect.name == "sqlite"
        and not connection.connection.driver_connection.in_transaction
    ):
        connection.exec_driver_sql("BEGIN")
