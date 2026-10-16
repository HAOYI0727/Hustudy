"""Owned course material packages and durable export job identity."""

from alembic import op
import sqlalchemy as sa

revision = "0008_material_exports"
down_revision = "0007_asset_organization"
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
        "material_exports",
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
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("processing_jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("zip_path", sa.String(500), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sources_json", sa.JSON(), nullable=False),
        sa.Column("counts_json", sa.JSON(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_material_exports_user_id", "material_exports", ["user_id"])
    op.create_index("ix_material_exports_course_id", "material_exports", ["course_id"])


def downgrade():
    raise RuntimeError("Use a reviewed backup restore for downgrade")
