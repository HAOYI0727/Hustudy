"""Protect version sequence and rebuild legacy indexes/previews after adoption."""

from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path
from alembic import op
import sqlalchemy as sa

revision = "0003_version_integrity"
down_revision = "0002_material_jobs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "uq_document_version_number",
        "document_versions",
        ["document_id", "version_no"],
        unique=True,
    )
    from app.services.search import index_version
    from sqlalchemy.orm import Session

    with Session(bind=op.get_bind()) as session:
        rows = session.execute(
            sa.text("""SELECT v.id, v.user_id, v.source_path FROM document_versions v
            JOIN documents d ON d.id=v.document_id WHERE v.parse_status='SUCCEEDED' AND d.deleted_at IS NULL""")
        ).all()
        for version_id, user_id, source in rows:
            index_version(session, version_id)
            if Path(source).suffix.lower() in {".pdf", ".pptx", ".docx"}:
                pending = session.execute(
                    sa.text(
                        "SELECT id FROM processing_jobs WHERE resource_id=:id AND type='PREVIEW'"
                    ),
                    {"id": version_id},
                ).first()
                if not pending:
                    now = datetime.now(timezone.utc)
                    session.execute(
                        sa.text("""INSERT INTO processing_jobs
                      (id,user_id,created_at,updated_at,type,status,resource_id,progress,attempt_count,max_attempts)
                      VALUES (:id,:u,:now,:now,'PREVIEW','QUEUED',:v,0,0,3)"""),
                        {"id": str(uuid4()), "u": user_id, "now": now, "v": version_id},
                    )
                    session.execute(
                        sa.text(
                            "UPDATE document_versions SET preview_status='QUEUED' WHERE id=:id"
                        ),
                        {"id": version_id},
                    )
        session.commit()


def downgrade():
    raise RuntimeError("Use a reviewed backup restore for downgrade")
