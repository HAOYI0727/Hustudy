"""Private portable package previews and atomic idempotent import receipts."""

from alembic import op
import sqlalchemy as sa

revision = "0022_portable_packages"
down_revision = "0021_bank_library"
branch_labels = depends_on = None


def owned_columns():
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade():
    op.create_table(
        "package_previews",
        *owned_columns(),
        sa.Column("artifact_path", sa.String(500), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_package_previews_user_id", "package_previews", ["user_id"])
    op.create_index(
        "ix_package_previews_expires_at", "package_previews", ["expires_at"]
    )
    op.create_table(
        "package_imports",
        *owned_columns(),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "request_id", name="uq_package_import_request"),
    )
    op.create_index("ix_package_imports_user_id", "package_imports", ["user_id"])


def downgrade():
    op.drop_table("package_imports")
    op.drop_table("package_previews")
