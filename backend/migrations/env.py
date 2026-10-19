from alembic import context
from sqlalchemy import ForeignKeyConstraint, create_engine, event, pool
from app.core.config import get_settings
from app.models import Base

config = context.config


def migrate(connection):
    def reflect_inline_fk_actions(constraint, table):
        # SQLite's inline REFERENCES clauses are omitted by SQLAlchemy 2.0's
        # DDL regex. Use SQLite's actual FK actions rather than rebuilding notes.
        if table.metadata is Base.metadata or table.name != "notes":
            return
        if list(constraint.column_keys) != ["folder_id"]:
            return
        for row in connection.exec_driver_sql('PRAGMA foreign_key_list("notes")'):
            if row[2:5] == ("note_folders", "folder_id", "id"):
                constraint.ondelete = row[6] if row[6] != "NO ACTION" else None
                break

    repair_reflection = connection.dialect.name == "sqlite"
    if repair_reflection:
        event.listen(ForeignKeyConstraint, "after_parent_attach", reflect_inline_fk_actions)
    context.configure(
        connection=connection, target_metadata=Base.metadata, compare_type=True, include_object=lambda obj, name, kind, reflected, compare_to: not (kind == "table" and name.startswith("chunk_search"))
    )
    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        if repair_reflection:
            event.remove(ForeignKeyConstraint, "after_parent_attach", reflect_inline_fk_actions)


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
