"""Add course organization, preserving all existing source identities."""

from alembic import op
import sqlalchemy as sa

revision = "0009_course_organization"
down_revision = "0008_material_exports"
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
        "courses",
        sa.Column("category", sa.String(64), nullable=False, server_default="未分类"),
    )
    op.add_column(
        "courses", sa.Column("tags", sa.JSON(), nullable=False, server_default="[]")
    )
    op.add_column(
        "courses",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade():
    raise RuntimeError("Use a reviewed backup restore for downgrade")
