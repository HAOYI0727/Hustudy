from alembic import context
from sqlalchemy import create_engine, pool
from app.core.config import get_settings
from app.models import Base

config = context.config


def migrate(connection):
    context.configure(
        connection=connection, target_metadata=Base.metadata, compare_type=True, include_object=lambda obj, name, kind, reflected, compare_to: not (kind == "table" and name.startswith("chunk_search"))
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=get_settings().database_url,
        target_metadata=Base.metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    connection = config.attributes.get("connection")
    if connection is not None:
        migrate(connection)
    else:
        engine = create_engine(get_settings().database_url, poolclass=pool.NullPool)
        with engine.connect() as connection:
            migrate(connection)
