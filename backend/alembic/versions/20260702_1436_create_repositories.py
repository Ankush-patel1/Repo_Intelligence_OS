"""create repositories table

Revision ID: 20260702_1436
Revises:
Create Date: 2026-07-02 14:36:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260702_1436"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.create_table(
        "repositories",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=512), nullable=False),
        sa.Column("branch", sa.String(length=255), nullable=False),
        sa.Column("clone_path", sa.String(length=1024), nullable=False),
        sa.Column("private", sa.Boolean(), nullable=False),
        sa.Column("default_branch", sa.String(length=255), nullable=False),
        sa.Column("last_synced", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner", "name", "branch", name="uq_repositories_owner_name_branch"),
    )
    op.create_index(op.f("ix_repositories_full_name"), "repositories", ["full_name"], unique=False)
    op.create_index(op.f("ix_repositories_name"), "repositories", ["name"], unique=False)
    op.create_index(op.f("ix_repositories_owner"), "repositories", ["owner"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_repositories_owner"), table_name="repositories")
    op.drop_index(op.f("ix_repositories_name"), table_name="repositories")
    op.drop_index(op.f("ix_repositories_full_name"), table_name="repositories")
    op.drop_table("repositories")
