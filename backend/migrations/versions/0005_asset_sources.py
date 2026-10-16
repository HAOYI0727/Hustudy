"""Preserve preview-page provenance and existing image references."""

from alembic import op
import sqlalchemy as sa

revision = "0005_asset_sources"
down_revision = "0004_document_organization"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    snapshot = None
    if connection.dialect.name == "sqlite":
        # Python sqlite3 legacy transaction mode does not BEGIN for DDL.
        # Start the physical transaction before any table recreation so failures
        # roll back the reference snapshot and parent table together.
        if not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        # Keep FK checks enabled. Existing references would otherwise be cascaded
        # away by SQLite batch recreation of their parent assets table.
        table_sql = connection.execute(
            sa.text(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='asset_references'"
            )
        ).scalar()
        if table_sql:
            indexes = (
                connection.execute(
                    sa.text(
                        "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='asset_references' AND sql IS NOT NULL"
                    )
                )
                .scalars()
                .all()
            )
            connection.exec_driver_sql(
                "CREATE TEMP TABLE asset_reference_migration_snapshot AS SELECT * FROM asset_references"
            )
            snapshot = (table_sql, indexes)
            op.drop_table("asset_references")
    with op.batch_alter_table("assets") as batch:
        batch.add_column(sa.Column("source_version_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("source_page", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("source_locator_type", sa.String(32), nullable=True))
        batch.create_foreign_key(
            "fk_asset_source_version",
            "document_versions",
            ["source_version_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index("ix_assets_source_version_id", ["source_version_id"])
    if snapshot:
        connection.exec_driver_sql(snapshot[0])
        connection.exec_driver_sql(
            "INSERT INTO asset_references SELECT * FROM asset_reference_migration_snapshot"
        )
        for sql in snapshot[1]:
            connection.exec_driver_sql(sql)
        connection.exec_driver_sql("DROP TABLE asset_reference_migration_snapshot")
        if connection.exec_driver_sql("PRAGMA foreign_key_check").first():
            raise RuntimeError("Image-source migration failed foreign-key validation")


def downgrade():
    raise RuntimeError("Use a reviewed backup restore for downgrade")
