import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Query
from app.schemas import QueryCreate, QueryResponse
from app.services.query_engine import process_query

router = APIRouter(prefix="/api")


@router.post("/query", response_model=QueryResponse)
async def submit_query(body: QueryCreate, session: AsyncSession = Depends(get_session)):
    q = Query(question=body.question)
    session.add(q)
    await session.commit()
    await session.refresh(q)

    asyncio.create_task(process_query(str(q.id)))

    return q


@router.get("/query/{query_id}", response_model=QueryResponse)
async def get_query(query_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    q = await session.get(Query, query_id)
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    return q
