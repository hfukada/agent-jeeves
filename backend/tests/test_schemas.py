"""Tests for Pydantic schemas."""

import uuid
from datetime import datetime, timezone

from app.schemas import OrgCreate, QueryCreate, RepoUpdate, QueryResponse


class TestOrgCreate:
    def test_valid(self):
        org = OrgCreate(name="myorg")
        assert org.name == "myorg"


class TestQueryCreate:
    def test_with_org(self):
        qid = uuid.uuid4()
        q = QueryCreate(question="Where is auth?", org_id=qid)
        assert q.question == "Where is auth?"
        assert q.org_id == qid

    def test_without_org(self):
        q = QueryCreate(question="What frameworks are used?")
        assert q.org_id is None


class TestRepoUpdate:
    def test_partial_update(self):
        update = RepoUpdate(summary="New summary")
        data = update.model_dump(exclude_unset=True)
        assert data == {"summary": "New summary"}
        assert "languages" not in data

    def test_multiple_fields(self):
        update = RepoUpdate(languages=["Python", "Go"], deployment_pattern="kubernetes")
        data = update.model_dump(exclude_unset=True)
        assert data["languages"] == ["Python", "Go"]
        assert data["deployment_pattern"] == "kubernetes"
        assert "summary" not in data


class TestQueryResponse:
    def test_from_dict(self):
        now = datetime.now(timezone.utc)
        resp = QueryResponse(
            id=uuid.uuid4(),
            question="test?",
            status="done",
            answer="answer here",
            sources=[{"repo": "org/repo", "files": ["main.py"], "score": 0.95}],
            created_at=now,
            completed_at=now,
        )
        assert resp.status == "done"
        assert len(resp.sources) == 1
