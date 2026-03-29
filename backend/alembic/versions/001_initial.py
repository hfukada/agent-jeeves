"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text, unique=True, nullable=False),
        sa.Column("github_token_hash", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "repositories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("github_full_name", sa.Text, unique=True, nullable=False),
        sa.Column("default_branch", sa.Text, nullable=True),
        sa.Column("clone_url", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("languages", JSONB, server_default="[]"),
        sa.Column("frameworks", JSONB, server_default="[]"),
        sa.Column("deployment_pattern", sa.Text, nullable=True),
        sa.Column("test_commands", JSONB, server_default="[]"),
        sa.Column("lint_commands", JSONB, server_default="[]"),
        sa.Column("docker_build", sa.Text, nullable=True),
        sa.Column("last_commit_sha", sa.Text, nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_repos_org", "repositories", ["org_id"])

    op.create_table(
        "queries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("answer", sa.Text, nullable=True),
        sa.Column("sources", JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "indexing_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("progress", JSONB, server_default="{}"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("indexing_jobs")
    op.drop_table("queries")
    op.drop_index("idx_repos_org")
    op.drop_table("repositories")
    op.drop_table("organizations")
