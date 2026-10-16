"""Immutable version metadata, durable worker leases and rebuildable FTS5 index."""

from alembic import op
import sqlalchemy as sa

revision = "0002_material_jobs"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade():
    for column in [
        sa.Column(
            "original_filename", sa.String(255), nullable=False, server_default=""
        ),
        sa.Column(
            "mime_type",
            sa.String(120),
            nullable=False,
            server_default="application/octet-stream",
        ),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sha256", sa.String(64), nullable=False, server_default=""),
        sa.Column("preview_path", sa.String(500), nullable=True),
        sa.Column("preview_error", sa.Text(), nullable=True),
        sa.Column(
            "tokenizer_version",
            sa.String(40),
            nullable=False,
            server_default="zh-bigram-v1",
        ),
    ]:
        op.add_column("document_versions", column)
    for column in [
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.String(36), nullable=True),
    ]:
        op.add_column("processing_jobs", column)
    op.execute("""UPDATE document_versions SET
      original_filename=(SELECT original_filename FROM documents WHERE id=document_id),
      mime_type=(SELECT mime_type FROM documents WHERE id=document_id),
      size_bytes=(SELECT size_bytes FROM documents WHERE id=document_id),
      sha256=(SELECT sha256 FROM documents WHERE id=document_id)""")
    # Creating the virtual table also verifies that this SQLite supports FTS5.
    op.execute(
        "CREATE VIRTUAL TABLE chunk_search USING fts5(chunk_id UNINDEXED, tokens)"
    )
    # Existing raw text is indexed using the same tokenizer as new imports.
    from app.services.search import index_version
    from sqlalchemy.orm import Session

    with Session(bind=op.get_bind()) as session:
        ids = (
            session.execute(
                sa.text(
                    "SELECT id FROM document_versions WHERE parse_status='SUCCEEDED'"
                )
            )
            .scalars()
            .all()
        )
        for version_id in ids:
            index_version(session, version_id)


def downgrade():
    raise RuntimeError(
        "Material migration downgrade requires a reviewed backup restore"
    )
