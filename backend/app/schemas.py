import uuid
from datetime import datetime

from pydantic import BaseModel


class OrgCreate(BaseModel):
    name: str


class OrgResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    last_indexed_at: datetime | None

    model_config = {"from_attributes": True}


class IndexJobResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    status: str
    progress: dict
    error: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class RepoResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    github_full_name: str
    default_branch: str | None
    summary: str | None
    languages: list
    frameworks: list
    deployment_pattern: str | None
    test_commands: list
    lint_commands: list
    docker_build: str | None
    indexed_at: datetime | None

    model_config = {"from_attributes": True}


class RepoUpdate(BaseModel):
    summary: str | None = None
    languages: list | None = None
    frameworks: list | None = None
    deployment_pattern: str | None = None
    test_commands: list | None = None
    lint_commands: list | None = None
    docker_build: str | None = None


class GithubRepoPreview(BaseModel):
    full_name: str
    description: str | None
    private: bool
    default_branch: str | None = None
    language: str | None = None
    html_url: str | None = None


class TriggerIndexRequest(BaseModel):
    repo_names: list[str] | None = None


class RegisterReposRequest(BaseModel):
    full_names: list[str]  # e.g. ["owner/repo1", "owner/repo2"]


class QueryCreate(BaseModel):
    question: str
    org_id: uuid.UUID | None = None


class QueryResponse(BaseModel):
    id: uuid.UUID
    question: str
    status: str
    answer: str | None
    sources: list
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
