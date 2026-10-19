"""Persist M3 note tags without changing existing content or source identities."""

from alembic import op
import sqlalchemy as sa

revision = "0013_note_tags"
down_revision = "0012_account_archives"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "notes", sa.Column("tags", sa.JSON(), server_default="[]", nullable=False)
    )


def downgrade():
    raise RuntimeError("Use a reviewed backup restore for downgrade")
