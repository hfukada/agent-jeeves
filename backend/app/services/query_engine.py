import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session
from app.models import Query, Repository
from app.services.embedding import embed_text, get_chroma_client

logger = logging.getLogger(__name__)

TOP_K = 20


async def process_query(query_id: str) -> None:
    """Process a query: embed, search ChromaDB, compose answer."""
    async with async_session() as session:
        q = await session.get(Query, query_id)
        if not q:
            logger.error(f"Query {query_id} not found")
            return

        question = q.question
        await session.execute(
            update(Query).where(Query.id == query_id).values(status="processing")
        )
        await session.commit()

    try:
        # Embed the question
        embeddings = await embed_text([question])
        query_embedding = embeddings[0]

        # Search ChromaDB
        client = get_chroma_client()
        collection = client.get_or_create_collection(
            name="code_chunks",
            metadata={"hnsw:space": "cosine"},
        )

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=TOP_K,
            include=["documents", "metadatas", "distances"],
        )

        if not results["ids"][0]:
            answer = "No relevant code found. Make sure repositories have been indexed."
            sources = []
        else:
            # Group results by repo
            repo_chunks: dict[str, list[dict]] = {}
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                doc = results["documents"][0][i]
                repo_id = meta["repo_id"]

                if repo_id not in repo_chunks:
                    repo_chunks[repo_id] = []
                repo_chunks[repo_id].append({
                    "file_path": meta["file_path"],
                    "language": meta["language"],
                    "chunk_type": meta["chunk_type"],
                    "distance": distance,
                    "snippet": doc[:300],
                })

            # Fetch repo metadata
            sources = []
            answer_parts = []
            async with async_session() as session:
                for repo_id, chunks in repo_chunks.items():
                    repo = await session.get(Repository, repo_id)
                    if not repo:
                        continue

                    best_score = min(c["distance"] for c in chunks)
                    files = list({c["file_path"] for c in chunks})

                    sources.append({
                        "repo": repo.github_full_name,
                        "files": files[:5],
                        "score": round(1 - best_score, 3),
                    })

                    answer_parts.append(
                        f"**{repo.github_full_name}** (relevance: {round(1 - best_score, 3)})\n"
                        f"  Summary: {(repo.summary or 'N/A')[:200]}\n"
                        f"  Languages: {', '.join(repo.languages) if repo.languages else 'N/A'}\n"
                        f"  Frameworks: {', '.join(repo.frameworks) if repo.frameworks else 'N/A'}\n"
                        f"  Relevant files: {', '.join(files[:5])}"
                    )

            # Sort by relevance
            sources.sort(key=lambda s: s["score"], reverse=True)
            answer_parts_sorted = sorted(answer_parts, key=lambda p: -float(p.split("relevance: ")[1].split(")")[0]))
            answer = f"Found relevant code in {len(repo_chunks)} repositories:\n\n" + "\n\n".join(answer_parts_sorted)

        # Save result
        async with async_session() as session:
            await session.execute(
                update(Query)
                .where(Query.id == query_id)
                .values(
                    status="done",
                    answer=answer,
                    sources=sources,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

        logger.info(f"Query {query_id} completed")

    except Exception as e:
        logger.exception(f"Query {query_id} failed")
        async with async_session() as session:
            await session.execute(
                update(Query)
                .where(Query.id == query_id)
                .values(
                    status="error",
                    answer=f"Error: {e}",
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()
