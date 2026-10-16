"""Owned account backup/restore control records; business tables remain unchanged."""

from alembic import op
import sqlalchemy as sa

revision = "0012_account_archives"
down_revision = "0011_remote_queries"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if (
        connection.dialect.name == "sqlite"
        and not connection.connection.driver_connection.in_transaction
    ):
        connection.exec_driver_sql("BEGIN IMMEDIATE")
    op.create_table(
        "account_archives",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("processing_jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("artifact_path", sa.String(500), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("counts", sa.JSON(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
    )
    op.create_index("ix_account_archives_user_id", "account_archives", ["user_id"])


def downgrade():
    raise RuntimeError("Use a reviewed backup restore for downgrade")
