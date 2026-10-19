"""Derived M3 knowledge ZIP jobs; no business data changes."""

from alembic import op
import sqlalchemy as sa

revision = "0014_note_exports"
down_revision = "0013_note_tags"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "note_exports",
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
            "job_id",
            sa.String(36),
            sa.ForeignKey("processing_jobs.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("zip_path", sa.String(500)),
        sa.Column("sha256", sa.String(64)),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sources_json", sa.JSON(), nullable=False),
        sa.Column("counts_json", sa.JSON(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_note_exports_user_id", "note_exports", ["user_id"])


def downgrade():
    raise RuntimeError("Use a reviewed backup restore for downgrade")
