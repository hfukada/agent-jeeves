import asyncio
import logging
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session
from app.models import IndexingJob, Organization, Repository
from app.services import github_client
from app.services.embedding import chunk_repository, store_chunks
from app.services.repo_analyzer import analyze_repo

logger = logging.getLogger(__name__)

# Limit concurrent repo processing
CONCURRENCY = 4


async def run_indexing_job(job_id: str, org_id: str, token: str) -> None:
    """Run the full indexing pipeline for an organization."""
    async with async_session() as session:
        await session.execute(
            update(IndexingJob)
            .where(IndexingJob.id == job_id)
            .values(status="running")
        )
        await session.commit()

    try:
        # Get org name
        async with async_session() as session:
            org = await session.get(Organization, org_id)
            if not org:
                raise ValueError(f"Organization {org_id} not found")
            org_name = org.name

        # List repos
        repos = await github_client.list_repos(org_name, token)
        total = len(repos)
        logger.info(f"Found {total} repos for {org_name}")

        await _update_job_progress(job_id, {"total": total, "done": 0, "current_repo": ""})

        sem = asyncio.Semaphore(CONCURRENCY)
        done_count = 0

        async def process_one(repo_info: github_client.RepoInfo) -> None:
            nonlocal done_count
            async with sem:
                await _update_job_progress(job_id, {
                    "total": total, "done": done_count, "current_repo": repo_info.full_name
                })
                await _process_repo(org_id, repo_info, token)
                done_count += 1
                await _update_job_progress(job_id, {
                    "total": total, "done": done_count, "current_repo": ""
                })

        await asyncio.gather(*[process_one(r) for r in repos], return_exceptions=True)

        # Mark org as indexed
        async with async_session() as session:
            await session.execute(
                update(Organization)
                .where(Organization.id == org_id)
                .values(last_indexed_at=datetime.now(timezone.utc))
            )
            await session.commit()

        # Mark job done
        async with async_session() as session:
            await session.execute(
                update(IndexingJob)
                .where(IndexingJob.id == job_id)
                .values(status="done", completed_at=datetime.now(timezone.utc))
            )
            await session.commit()

        logger.info(f"Indexing job {job_id} completed")

    except Exception as e:
        logger.exception(f"Indexing job {job_id} failed")
        async with async_session() as session:
            await session.execute(
                update(IndexingJob)
                .where(IndexingJob.id == job_id)
                .values(status="error", error=str(e), completed_at=datetime.now(timezone.utc))
            )
            await session.commit()


async def _process_repo(org_id: str, repo_info: github_client.RepoInfo, token: str) -> None:
    """Clone, analyze, embed, and store a single repository."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="jeeves_"))
    try:
        logger.info(f"Processing {repo_info.full_name}")
        repo_path = await github_client.clone_repo(repo_info.clone_url, token, tmp_dir)

        # Analyze
        analysis = analyze_repo(repo_path)

        # Upsert to database
        async with async_session() as session:
            result = await session.execute(
                select(Repository).where(Repository.github_full_name == repo_info.full_name)
            )
            repo = result.scalar_one_or_none()

            if repo:
                repo.summary = analysis.summary
                repo.languages = analysis.languages
                repo.frameworks = analysis.frameworks
                repo.deployment_pattern = analysis.deployment_pattern
                repo.test_commands = analysis.test_commands
                repo.lint_commands = analysis.lint_commands
                repo.docker_build = analysis.docker_build
                repo.default_branch = repo_info.default_branch
                repo.indexed_at = datetime.now(timezone.utc)
            else:
                repo = Repository(
                    org_id=org_id,
                    github_full_name=repo_info.full_name,
                    clone_url=repo_info.clone_url,
                    default_branch=repo_info.default_branch,
                    summary=analysis.summary,
                    languages=analysis.languages,
                    frameworks=analysis.frameworks,
                    deployment_pattern=analysis.deployment_pattern,
                    test_commands=analysis.test_commands,
                    lint_commands=analysis.lint_commands,
                    docker_build=analysis.docker_build,
                    indexed_at=datetime.now(timezone.utc),
                )
                session.add(repo)

            await session.commit()
            await session.refresh(repo)
            repo_id = str(repo.id)

        # Chunk and embed
        chunks = chunk_repository(repo_path, repo_info.full_name)
        await store_chunks(repo_id, chunks)

        logger.info(f"Done processing {repo_info.full_name}: {len(chunks)} chunks")

    except Exception:
        logger.exception(f"Failed to process {repo_info.full_name}")
        raise
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def _update_job_progress(job_id: str, progress: dict) -> None:
    async with async_session() as session:
        await session.execute(
            update(IndexingJob)
            .where(IndexingJob.id == job_id)
            .values(progress=progress)
        )
        await session.commit()
