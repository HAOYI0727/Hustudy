"""Separate question-bank files from the material reading catalogue."""

from alembic import op
import sqlalchemy as sa

revision = "0021_bank_library"
down_revision = "0020_exam_analysis"
branch_labels = depends_on = None


def upgrade():
    op.add_column(
        "documents",
        sa.Column(
            "library_scope", sa.String(24), nullable=False, server_default="material"
        ),
    )
    op.create_index("ix_documents_library_scope", "documents", ["library_scope"])


def downgrade():
    op.drop_index("ix_documents_library_scope", table_name="documents")
    op.drop_column("documents", "library_scope")
