"""Versioned exam statistics and stable topic merge identities."""

from alembic import op
import sqlalchemy as sa

revision = "0020_exam_analysis"
down_revision = "0019_exam_bank"
branch_labels = depends_on = None


def upgrade():
    op.add_column(
        "topics",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("topics", sa.Column("merged_into_id", sa.String(36), nullable=True))
    op.add_column(
        "topics",
        sa.Column("sources_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_table(
        "exam_analysis_reports",
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
            "course_id",
            sa.String(36),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("report_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
    )
    op.create_index(
        "ix_exam_analysis_reports_user_id", "exam_analysis_reports", ["user_id"]
    )
    op.create_index(
        "ix_exam_analysis_reports_course_id", "exam_analysis_reports", ["course_id"]
    )


def downgrade():
    op.drop_table("exam_analysis_reports")
    op.drop_column("topics", "sources_json")
    op.drop_column("topics", "merged_into_id")
    op.drop_column("topics", "revision")
