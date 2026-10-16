"""Frozen initial schema; validated adoption of the original development database."""

from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

EXPECTED = {
    "users": [
        "id",
        "username",
        "password_hash",
        "timezone",
        "created_at",
        "updated_at",
    ],
    "courses": ["name", "description", "id", "user_id", "created_at", "updated_at"],
    "feedback": [
        "kind",
        "content",
        "rating",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "processing_jobs": [
        "type",
        "status",
        "resource_id",
        "progress",
        "error",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "ai_results": [
        "course_id",
        "query",
        "result_json",
        "status",
        "model_mode",
        "prompt_version",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "assets": [
        "course_id",
        "original_filename",
        "mime_type",
        "size_bytes",
        "sha256",
        "storage_path",
        "alt",
        "deleted",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "documents": [
        "course_id",
        "name",
        "original_filename",
        "mime_type",
        "size_bytes",
        "sha256",
        "storage_path",
        "deleted_at",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "exam_blueprints": [
        "course_id",
        "name",
        "config_json",
        "status",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "notes": [
        "course_id",
        "title",
        "content",
        "revision",
        "deleted",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "past_papers": [
        "course_id",
        "title",
        "year",
        "content",
        "review_status",
        "content_hash",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "topics": [
        "course_id",
        "name",
        "aliases_json",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "asset_references": [
        "note_id",
        "asset_id",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "document_versions": [
        "document_id",
        "version_no",
        "parse_status",
        "preview_status",
        "index_status",
        "parse_error",
        "source_path",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "exam_papers": [
        "course_id",
        "blueprint_id",
        "title",
        "mode",
        "status",
        "questions_json",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "note_links": [
        "source_note_id",
        "target_note_id",
        "label",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "past_questions": [
        "paper_id",
        "number",
        "stem",
        "question_type",
        "points",
        "answer",
        "answer_source",
        "status",
        "topic_id",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "document_chunks": [
        "version_id",
        "ordinal",
        "locator_type",
        "locator_value",
        "text",
        "start_offset",
        "end_offset",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "exam_attempts": [
        "paper_id",
        "status",
        "answers_json",
        "score",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "citations": [
        "note_id",
        "version_id",
        "chunk_id",
        "locator_type",
        "locator_value",
        "quote",
        "quote_hash",
        "availability",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "mistakes": [
        "attempt_id",
        "question_id",
        "detail_json",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
    "review_tasks": [
        "mistake_id",
        "title",
        "due_date",
        "status",
        "id",
        "user_id",
        "created_at",
        "updated_at",
    ],
}


def upgrade():
    inspector = sa.inspect(op.get_bind())
    existing = set(inspector.get_table_names()) - {"alembic_version"}
    if existing:
        if existing != set(EXPECTED):
            raise RuntimeError(
                "Existing database differs from baseline; manual review required"
            )
        for name, columns in EXPECTED.items():
            if set(columns) != {
                column["name"] for column in inspector.get_columns(name)
            }:
                raise RuntimeError("Existing schema differs: " + name)
        return
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_table(
        "courses",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_courses_user_id"), "courses", ["user_id"], unique=False)
    op.create_table(
        "feedback",
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feedback_user_id"), "feedback", ["user_id"], unique=False)
    op.create_table(
        "processing_jobs",
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_processing_jobs_resource_id"),
        "processing_jobs",
        ["resource_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_processing_jobs_user_id"), "processing_jobs", ["user_id"], unique=False
    )
    op.create_table(
        "ai_results",
        sa.Column("course_id", sa.String(length=36), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("model_mode", sa.String(length=24), nullable=False),
        sa.Column("prompt_version", sa.String(length=40), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_results_course_id"), "ai_results", ["course_id"], unique=False
    )
    op.create_index(
        op.f("ix_ai_results_user_id"), "ai_results", ["user_id"], unique=False
    )
    op.create_table(
        "assets",
        sa.Column("course_id", sa.String(length=36), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("alt", sa.String(length=500), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assets_course_id"), "assets", ["course_id"], unique=False)
    op.create_index(op.f("ix_assets_sha256"), "assets", ["sha256"], unique=False)
    op.create_index(op.f("ix_assets_user_id"), "assets", ["user_id"], unique=False)
    op.create_table(
        "documents",
        sa.Column("course_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_documents_course_id"), "documents", ["course_id"], unique=False
    )
    op.create_index(op.f("ix_documents_sha256"), "documents", ["sha256"], unique=False)
    op.create_index(
        op.f("ix_documents_user_id"), "documents", ["user_id"], unique=False
    )
    op.create_table(
        "exam_blueprints",
        sa.Column("course_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_exam_blueprints_course_id"),
        "exam_blueprints",
        ["course_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_exam_blueprints_user_id"), "exam_blueprints", ["user_id"], unique=False
    )
    op.create_table(
        "notes",
        sa.Column("course_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notes_course_id"), "notes", ["course_id"], unique=False)
    op.create_index(op.f("ix_notes_user_id"), "notes", ["user_id"], unique=False)
    op.create_table(
        "past_papers",
        sa.Column("course_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_past_papers_content_hash"),
        "past_papers",
        ["content_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_past_papers_course_id"), "past_papers", ["course_id"], unique=False
    )
    op.create_index(
        op.f("ix_past_papers_user_id"), "past_papers", ["user_id"], unique=False
    )
    op.create_table(
        "topics",
        sa.Column("course_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("aliases_json", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_topics_course_id"), "topics", ["course_id"], unique=False)
    op.create_index(op.f("ix_topics_user_id"), "topics", ["user_id"], unique=False)
    op.create_table(
        "asset_references",
        sa.Column("note_id", sa.String(length=36), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_asset_references_asset_id"),
        "asset_references",
        ["asset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_asset_references_note_id"),
        "asset_references",
        ["note_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_asset_references_user_id"),
        "asset_references",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "document_versions",
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("parse_status", sa.String(length=32), nullable=False),
        sa.Column("preview_status", sa.String(length=32), nullable=False),
        sa.Column("index_status", sa.String(length=32), nullable=False),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("source_path", sa.String(length=500), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_versions_document_id"),
        "document_versions",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_versions_user_id"),
        "document_versions",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "exam_papers",
        sa.Column("course_id", sa.String(length=36), nullable=False),
        sa.Column("blueprint_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("mode", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("questions_json", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["blueprint_id"], ["exam_blueprints.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_exam_papers_course_id"), "exam_papers", ["course_id"], unique=False
    )
    op.create_index(
        op.f("ix_exam_papers_user_id"), "exam_papers", ["user_id"], unique=False
    )
    op.create_table(
        "note_links",
        sa.Column("source_note_id", sa.String(length=36), nullable=False),
        sa.Column("target_note_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=240), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_note_links_source_note_id"),
        "note_links",
        ["source_note_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_note_links_target_note_id"),
        "note_links",
        ["target_note_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_note_links_user_id"), "note_links", ["user_id"], unique=False
    )
    op.create_table(
        "past_questions",
        sa.Column("paper_id", sa.String(length=36), nullable=False),
        sa.Column("number", sa.String(length=40), nullable=False),
        sa.Column("stem", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=32), nullable=False),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("answer_source", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("topic_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["past_papers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_past_questions_paper_id"), "past_questions", ["paper_id"], unique=False
    )
    op.create_index(
        op.f("ix_past_questions_topic_id"), "past_questions", ["topic_id"], unique=False
    )
    op.create_index(
        op.f("ix_past_questions_user_id"), "past_questions", ["user_id"], unique=False
    )
    op.create_table(
        "document_chunks",
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("locator_type", sa.String(length=32), nullable=False),
        sa.Column("locator_value", sa.String(length=120), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["version_id"], ["document_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_chunks_user_id"), "document_chunks", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_document_chunks_version_id"),
        "document_chunks",
        ["version_id"],
        unique=False,
    )
    op.create_table(
        "exam_attempts",
        sa.Column("paper_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("answers_json", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["exam_papers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_exam_attempts_paper_id"), "exam_attempts", ["paper_id"], unique=False
    )
    op.create_index(
        op.f("ix_exam_attempts_user_id"), "exam_attempts", ["user_id"], unique=False
    )
    op.create_table(
        "citations",
        sa.Column("note_id", sa.String(length=36), nullable=True),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=False),
        sa.Column("locator_type", sa.String(length=32), nullable=False),
        sa.Column("locator_value", sa.String(length=120), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("quote_hash", sa.String(length=64), nullable=False),
        sa.Column("availability", sa.String(length=24), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["version_id"], ["document_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_citations_chunk_id"), "citations", ["chunk_id"], unique=False
    )
    op.create_index(
        op.f("ix_citations_note_id"), "citations", ["note_id"], unique=False
    )
    op.create_index(
        op.f("ix_citations_user_id"), "citations", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_citations_version_id"), "citations", ["version_id"], unique=False
    )
    op.create_table(
        "mistakes",
        sa.Column("attempt_id", sa.String(length=36), nullable=False),
        sa.Column("question_id", sa.String(length=36), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attempt_id"], ["exam_attempts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mistakes_attempt_id"), "mistakes", ["attempt_id"], unique=False
    )
    op.create_index(op.f("ix_mistakes_user_id"), "mistakes", ["user_id"], unique=False)
    op.create_table(
        "review_tasks",
        sa.Column("mistake_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("due_date", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["mistake_id"], ["mistakes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_review_tasks_user_id"), "review_tasks", ["user_id"], unique=False
    )
    # ### end Alembic commands ###


def downgrade():
    raise RuntimeError("Baseline downgrade is disabled to protect user data")
