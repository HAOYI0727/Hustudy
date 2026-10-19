"""Recoverable note trash and per-account retention, without table rebuilds."""

from alembic import op
import sqlalchemy as sa

revision = "0016_note_trash"
down_revision = "0015_note_folders"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("notes", sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.add_column("notes", sa.Column("purge_after", sa.DateTime(timezone=True)))
    op.create_index("ix_notes_purge_after", "notes", ["purge_after"])
    # Previous deletions have no reliable deletion date. Give them a full window.
    op.execute(
        "UPDATE notes SET deleted_at=CURRENT_TIMESTAMP, "
        "purge_after=datetime('now', '+30 days') WHERE deleted=1"
    )
    op.create_table(
        "note_trash_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("retention_days", sa.Integer(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        "ix_note_trash_policies_user_id", "note_trash_policies", ["user_id"]
    )


def downgrade():
    raise RuntimeError("Use a reviewed backup restore for downgrade")
