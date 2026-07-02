"""create repository files table

Revision ID: 20260702_1715
Revises: 20260702_1436
Create Date: 2026-07-02 17:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260702_1715"
down_revision: str | None = "20260702_1436"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "repository_files",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("absolute_path", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("extension", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("line_count", sa.Integer(), nullable=True),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("last_modified", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_binary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repository_files_repository_id", "repository_files", ["repository_id"])
    op.create_index("ix_repository_files_language", "repository_files", ["language"])
    op.create_index("ix_repository_files_relative_path", "repository_files", ["relative_path"])


def downgrade() -> None:
    op.drop_index("ix_repository_files_relative_path", table_name="repository_files")
    op.drop_index("ix_repository_files_language", table_name="repository_files")
    op.drop_index("ix_repository_files_repository_id", table_name="repository_files")
    op.drop_table("repository_files")
