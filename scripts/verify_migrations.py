"""Build a disposable SQLite database and verify the ORM has no migration drift."""
from pathlib import Path
from tempfile import TemporaryDirectory
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

with TemporaryDirectory(prefix='hustudy-migration-check-') as folder:
    config = Config(str(Path(__file__).resolve().parents[1] / 'backend/alembic.ini'))
    engine = create_engine(f'sqlite:///{folder}/verify.db')
    try:
        with engine.begin() as connection:
            config.attributes['connection'] = connection
            command.upgrade(config, 'head')
            command.check(config)
    finally:
        engine.dispose()
print('Migration upgrade and model drift check passed (temporary database).')
