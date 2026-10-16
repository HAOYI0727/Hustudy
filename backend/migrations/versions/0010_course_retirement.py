"""Retain course identity for unavailable citations after course removal."""

from alembic import op
import sqlalchemy as sa

revision = "0010_course_retirement"
down_revision = "0009_course_organization"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if (
        connection.dialect.name == "sqlite"
        and not connection.connection.driver_connection.in_transaction
    ):
        connection.exec_driver_sql("BEGIN IMMEDIATE")
    op.add_column(
        "courses", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    raise RuntimeError("Use a reviewed backup restore for downgrade")
