"""Organize notes without recreating notes or changing existing references."""

from alembic import op
import sqlalchemy as sa

revision = "0015_note_folders"
down_revision = "0014_note_exports"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "note_folders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            sa.String(36),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            sa.String(36),
            sa.ForeignKey("note_folders.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for field in ("user_id", "course_id", "parent_id"):
        op.create_index(f"ix_note_folders_{field}", "note_folders", [field])
    # SQLite supports this nullable inline FK. A batch table rebuild could
    # cascade-delete existing note links, citations and asset references.
    op.execute(
        "ALTER TABLE notes ADD COLUMN folder_id VARCHAR(36) REFERENCES note_folders(id) ON DELETE SET NULL"
    )
    op.create_index("ix_notes_folder_id", "notes", ["folder_id"])


def downgrade():
    raise RuntimeError("Use a reviewed backup restore for downgrade")
