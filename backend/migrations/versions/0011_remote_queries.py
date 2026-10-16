"""Owned source previews and explicit remote-query consent."""

from alembic import op
import sqlalchemy as sa

revision = "0011_remote_queries"
down_revision = "0010_course_retirement"
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
        "remote_queries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "course_id",
            sa.String(36),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("endpoint", sa.String(500), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("processing_jobs.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "result_id",
            sa.String(36),
            sa.ForeignKey("ai_results.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_remote_queries_user_id", "remote_queries", ["user_id"])
    op.create_index("ix_remote_queries_course_id", "remote_queries", ["course_id"])


def downgrade():
    raise RuntimeError("Use a reviewed backup restore for downgrade")
