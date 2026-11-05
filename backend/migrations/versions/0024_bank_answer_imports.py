"""Private answer matching preview and checkpoints."""

from alembic import op
import sqlalchemy as sa

revision = "0024_bank_answer_imports"
down_revision = "0023_course_agenda"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "bank_answer_imports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "course_id",
            sa.String(36),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "paper_id",
            sa.String(36),
            sa.ForeignKey("past_papers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scope_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("processing_jobs.id", ondelete="SET NULL"),
        ),
    )


def downgrade():
    op.drop_table("bank_answer_imports")
