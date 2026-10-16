"""Independent, confirmed manual PDF transcripts without rewriting original chunks."""

from alembic import op
import sqlalchemy as sa

revision = "0006_manual_transcripts"
down_revision = "0005_asset_sources"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "document_chunks",
        sa.Column(
            "source_kind", sa.String(32), nullable=False, server_default="extracted"
        ),
    )
    op.add_column(
        "citations",
        sa.Column(
            "source_kind", sa.String(32), nullable=False, server_default="extracted"
        ),
    )
    op.create_table(
        "manual_transcripts",
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
            "version_id",
            sa.String(36),
            sa.ForeignKey("document_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "supersedes_id",
            sa.String(36),
            sa.ForeignKey("manual_transcripts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "chunk_id",
            sa.String(36),
            sa.ForeignKey("document_chunks.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "confirmed_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_manual_transcripts_user_id", "manual_transcripts", ["user_id"])
    op.create_index(
        "ix_manual_transcripts_version_id", "manual_transcripts", ["version_id"]
    )
    op.create_index(
        "uq_manual_current_page",
        "manual_transcripts",
        ["version_id", "page"],
        unique=True,
        sqlite_where=sa.text("status = 'CONFIRMED'"),
    )


def downgrade():
    raise RuntimeError("Use a reviewed backup restore for downgrade")
