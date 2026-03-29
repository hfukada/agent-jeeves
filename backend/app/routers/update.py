import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Repository
from app.schemas import RepoResponse, RepoUpdate

router = APIRouter(prefix="/api")


@router.patch("/repos/{repo_id}", response_model=RepoResponse)
async def update_repo(repo_id: uuid.UUID, body: RepoUpdate, session: AsyncSession = Depends(get_session)):
    repo = await session.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(repo, field, value)

    await session.commit()
    await session.refresh(repo)
    return repo
