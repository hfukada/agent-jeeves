import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

TZDateTime = DateTime(timezone=True)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    github_token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    last_indexed_at: Mapped[datetime | None] = mapped_column(TZDateTime, default=None)


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    github_full_name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    default_branch: Mapped[str | None] = mapped_column(Text)
    clone_url: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    languages: Mapped[dict] = mapped_column(JSONB, default=list)
    frameworks: Mapped[dict] = mapped_column(JSONB, default=list)
    deployment_pattern: Mapped[str | None] = mapped_column(Text)
    test_commands: Mapped[dict] = mapped_column(JSONB, default=list)
    lint_commands: Mapped[dict] = mapped_column(JSONB, default=list)
    docker_build: Mapped[str | None] = mapped_column(Text)
    last_commit_sha: Mapped[str | None] = mapped_column(Text)
    indexed_at: Mapped[datetime | None] = mapped_column(TZDateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, onupdate=utcnow)


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    answer: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[dict] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(TZDateTime, default=None)


class IndexingJob(Base):
    __tablename__ = "indexing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    progress: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(TZDateTime, default=None)
