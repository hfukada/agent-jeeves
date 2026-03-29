import asyncio

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select

from app.db import async_session
from app.models import Organization, Query, Repository
from app.services.embedding import embed_text, get_chroma_client

mcp = FastMCP("Agent Jeeves", instructions="Code knowledge base for multi-repository organizations")


@mcp.tool()
async def search_code(query: str, org: str | None = None) -> str:
    """Semantic search across all indexed repositories. Returns relevant code chunks with file paths and scores."""
    embeddings = await embed_text([query])
    query_embedding = embeddings[0]

    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name="code_chunks",
        metadata={"hnsw:space": "cosine"},
    )

    where_filter = None
    if org:
        # Get repo IDs for this org
        async with async_session() as session:
            result = await session.execute(
                select(Organization).where(Organization.name == org)
            )
            org_obj = result.scalar_one_or_none()
            if org_obj:
                result = await session.execute(
                    select(Repository.id).where(Repository.org_id == org_obj.id)
                )
                repo_ids = [str(r[0]) for r in result.all()]
                if repo_ids:
                    where_filter = {"repo_id": {"$in": repo_ids}}

    kwargs = {"query_embeddings": [query_embedding], "n_results": 10, "include": ["documents", "metadatas", "distances"]}
    if where_filter:
        kwargs["where"] = where_filter

    results = collection.query(**kwargs)

    if not results["ids"][0]:
        return "No results found."

    output_parts = []
    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i]
        doc = results["documents"][0][i]
        score = round(1 - distance, 3)
        output_parts.append(
            f"[{score}] {meta.get('file_path', 'unknown')} ({meta.get('language', 'unknown')})\n{doc[:500]}"
        )

    return "\n\n---\n\n".join(output_parts)


@mcp.tool()
async def get_repo_info(repo_name: str) -> str:
    """Get structured metadata for a repository by its full name (e.g., 'org/repo')."""
    async with async_session() as session:
        result = await session.execute(
            select(Repository).where(Repository.github_full_name == repo_name)
        )
        repo = result.scalar_one_or_none()

    if not repo:
        return f"Repository '{repo_name}' not found."

    return (
        f"Repository: {repo.github_full_name}\n"
        f"Summary: {repo.summary or 'N/A'}\n"
        f"Languages: {', '.join(repo.languages) if repo.languages else 'N/A'}\n"
        f"Frameworks: {', '.join(repo.frameworks) if repo.frameworks else 'N/A'}\n"
        f"Deployment: {repo.deployment_pattern or 'N/A'}\n"
        f"Test commands: {', '.join(repo.test_commands) if repo.test_commands else 'N/A'}\n"
        f"Lint commands: {', '.join(repo.lint_commands) if repo.lint_commands else 'N/A'}\n"
        f"Docker build: {repo.docker_build or 'N/A'}\n"
        f"Indexed at: {repo.indexed_at or 'Never'}"
    )


@mcp.tool()
async def list_repos(org: str) -> str:
    """List all indexed repositories for an organization with brief summaries."""
    async with async_session() as session:
        result = await session.execute(
            select(Organization).where(Organization.name == org)
        )
        org_obj = result.scalar_one_or_none()
        if not org_obj:
            return f"Organization '{org}' not found."

        result = await session.execute(
            select(Repository)
            .where(Repository.org_id == org_obj.id)
            .order_by(Repository.github_full_name)
        )
        repos = result.scalars().all()

    if not repos:
        return f"No repositories indexed for '{org}'."

    lines = [f"Repositories for {org} ({len(repos)} total):\n"]
    for r in repos:
        langs = ", ".join(r.languages[:3]) if r.languages else "N/A"
        summary = (r.summary or "No summary")[:100]
        lines.append(f"- {r.github_full_name} [{langs}]: {summary}")

    return "\n".join(lines)


@mcp.tool()
async def ask(question: str) -> str:
    """Ask a high-level question about the codebase. Searches across all indexed repositories and returns a structured answer."""
    from app.services.query_engine import process_query as _process_query

    # Create query record
    async with async_session() as session:
        q = Query(question=question)
        session.add(q)
        await session.commit()
        await session.refresh(q)
        query_id = str(q.id)

    # Process synchronously for MCP (caller waits)
    await _process_query(query_id)

    # Fetch result
    async with async_session() as session:
        q = await session.get(Query, query_id)
        if not q:
            return "Query processing failed."
        return q.answer or "No answer generated."
