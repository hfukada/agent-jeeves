import asyncio
import uuid

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import IndexingJob, Organization, Repository
from app.schemas import IndexJobResponse, OrgCreate, OrgResponse, RepoResponse
from app.services.background import run_indexing_job

router = APIRouter(prefix="/api")


@router.post("/orgs", response_model=OrgResponse)
async def create_org(body: OrgCreate, session: AsyncSession = Depends(get_session)):
    # Check for existing org
    result = await session.execute(
        select(Organization).where(Organization.name == body.name)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Organization already exists")

    token_hash = bcrypt.hashpw(body.github_token.encode(), bcrypt.gensalt()).decode()
    org = Organization(name=body.name, github_token_hash=token_hash)
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return org


@router.post("/orgs/{org_id}/index")
async def trigger_index(org_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    org = await session.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check for already running job
    result = await session.execute(
        select(IndexingJob).where(
            IndexingJob.org_id == org_id,
            IndexingJob.status.in_(["pending", "running"]),
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Indexing job already running")

    job = IndexingJob(org_id=org_id)
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # The token needs to be provided again since we only store the hash.
    # For now, use the env var GITHUB_TOKEN.
    from app.config import settings
    if not settings.github_token:
        raise HTTPException(status_code=400, detail="GITHUB_TOKEN not configured")

    asyncio.create_task(run_indexing_job(str(job.id), str(org_id), settings.github_token))

    return {"job_id": job.id}


@router.get("/jobs/{job_id}", response_model=IndexJobResponse)
async def get_job(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    job = await session.get(IndexingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/orgs/{org_id}/repos", response_model=list[RepoResponse])
async def list_repos(org_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Repository).where(Repository.org_id == org_id).order_by(Repository.github_full_name)
    )
    return result.scalars().all()


@router.get("/repos/{repo_id}", response_model=RepoResponse)
async def get_repo(repo_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    repo = await session.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo
