"""Add mutable document labels without changing immutable content or citations."""

from alembic import op
import sqlalchemy as sa

revision = "0004_document_organization"
down_revision = "0003_version_integrity"
branch_labels = None
depends_on = None


def upgrade():
    # The exact tag filter requires SQLite JSON functions; fail before changing schema.
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        connection.execute(
            sa.text("SELECT value FROM json_each('[\"probe\"]')")
        ).scalar_one()
    op.add_column(
        "documents",
        sa.Column("category", sa.String(40), server_default="未分类", nullable=False),
    )
    op.add_column(
        "documents", sa.Column("tags", sa.JSON(), server_default="[]", nullable=False)
    )
    op.create_index("ix_documents_category", "documents", ["category"])


def downgrade():
    raise RuntimeError("Use a reviewed backup restore for downgrade")
