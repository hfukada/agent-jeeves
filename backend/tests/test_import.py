"""Smoke tests: verify all modules import without error."""


def test_import_config():
    from app.config import Settings
    s = Settings(database_url="postgresql+asyncpg://x:x@localhost/x")
    assert s.database_url.startswith("postgresql")


def test_import_models():
    from app.models import Organization, Repository, Query, IndexingJob, Base
    assert "organizations" in Base.metadata.tables
    assert "repositories" in Base.metadata.tables
    assert "queries" in Base.metadata.tables
    assert "indexing_jobs" in Base.metadata.tables


def test_import_schemas():
    from app.schemas import OrgCreate, OrgResponse, QueryCreate, QueryResponse, RepoUpdate, RepoResponse, IndexJobResponse
    # Verify they're all Pydantic models
    for cls in [OrgCreate, OrgResponse, QueryCreate, QueryResponse, RepoUpdate, RepoResponse, IndexJobResponse]:
        assert hasattr(cls, "model_fields")


def test_import_routers():
    from app.routers.indexing import router as indexing_router
    from app.routers.query import router as query_router
    from app.routers.update import router as update_router
    assert indexing_router.prefix == "/api"
    assert query_router.prefix == "/api"
    assert update_router.prefix == "/api"


def test_import_services():
    from app.services.github_client import list_repos, clone_repo
    from app.services.repo_analyzer import analyze_repo
    from app.services.embedding import chunk_repository, embed_text, store_chunks
    from app.services.query_engine import process_query
    from app.services.background import run_indexing_job
    assert callable(list_repos)
    assert callable(clone_repo)
    assert callable(analyze_repo)
    assert callable(chunk_repository)


def test_import_mcp():
    from app.mcp.server import mcp
    assert mcp.name == "Agent Jeeves"
