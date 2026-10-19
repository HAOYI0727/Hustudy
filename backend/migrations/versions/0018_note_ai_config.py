"""Per-account encrypted note AI credentials; not part of business archives."""

from alembic import op
import sqlalchemy as sa

revision = "0018_note_ai_config"
down_revision = "0017_note_capture"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "note_ai_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("encrypted_key", sa.Text(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
    )
    op.create_index("ix_note_ai_configs_user_id", "note_ai_configs", ["user_id"])


def downgrade():
    op.drop_table("note_ai_configs")
