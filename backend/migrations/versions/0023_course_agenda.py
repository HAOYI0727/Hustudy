"""Associate manually created schedules with courses."""
from alembic import op
import sqlalchemy as sa

revision = "0023_course_agenda"
down_revision = "0022_portable_packages"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("review_tasks") as batch:
        batch.add_column(sa.Column("course_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_review_tasks_course", "courses", ["course_id"], ["id"], ondelete="CASCADE")
        batch.create_index("ix_review_tasks_course_id", ["course_id"])


def downgrade():
    with op.batch_alter_table("review_tasks") as batch:
        batch.drop_index("ix_review_tasks_course_id")
        batch.drop_constraint("fk_review_tasks_course", type_="foreignkey")
        batch.drop_column("course_id")
