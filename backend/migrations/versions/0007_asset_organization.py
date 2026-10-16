"""Organize image metadata without changing immutable files or UUID references."""

from alembic import op
import sqlalchemy as sa

revision = "0007_asset_organization"
down_revision = "0006_manual_transcripts"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    # sqlite3 legacy mode does not begin a transaction for ADD COLUMN.
    # A failed backfill must roll back the columns as well as the revision.
    if (
        connection.dialect.name == "sqlite"
        and not connection.connection.driver_connection.in_transaction
    ):
        connection.exec_driver_sql("BEGIN IMMEDIATE")
    op.add_column(
        "assets", sa.Column("name", sa.String(255), nullable=False, server_default="")
    )
    op.execute("UPDATE assets SET name = original_filename")
    op.add_column(
        "assets", sa.Column("tags", sa.JSON(), nullable=False, server_default="[]")
    )
    op.add_column(
        "assets",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade():
    raise RuntimeError("Use a reviewed backup restore for downgrade")
