"""User supplied question banks and immutable attempt snapshots."""

from alembic import op
import sqlalchemy as sa

revision = "0019_exam_bank"
down_revision = "0018_note_ai_config"
branch_labels = depends_on = None


def upgrade():
    for table, name in (
        ("past_papers", "bank_meta_json"),
        ("past_questions", "bank_data_json"),
        ("exam_attempts", "snapshot_json"),
        ("exam_attempts", "grading_json"),
    ):
        op.add_column(
            table, sa.Column(name, sa.Text(), nullable=False, server_default="{}")
        )
    op.add_column(
        "past_questions",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade():
    op.drop_column("past_questions", "revision")
    for table, name in (
        ("exam_attempts", "grading_json"),
        ("exam_attempts", "snapshot_json"),
        ("past_questions", "bank_data_json"),
        ("past_papers", "bank_meta_json"),
    ):
        op.drop_column(table, name)
