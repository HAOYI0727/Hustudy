"""Disposable note recognition drafts, excluded from business archives."""

from alembic import op
import sqlalchemy as sa

revision = "0017_note_capture"
down_revision = "0016_note_trash"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "note_captures",
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
        sa.Column("filename", sa.String(240), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("ai_request", sa.JSON(), nullable=False),
        sa.Column("ai_result", sa.JSON(), nullable=False),
    )
    op.create_index("ix_note_captures_user_id", "note_captures", ["user_id"])


def downgrade():
    op.drop_table("note_captures")
