import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import engine
from app.models import Base
from app.routers import indexing, query, update

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Pull nomic-embed-text model on startup
    async with httpx.AsyncClient(timeout=600) as client:
        try:
            await client.post(
                f"{settings.ollama_base_url}/api/pull",
                json={"name": "nomic-embed-text"},
            )
        except httpx.ConnectError:
            pass  # Ollama may not be running in dev

    yield

    await engine.dispose()


app = FastAPI(title="Agent Jeeves", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(indexing.router)
app.include_router(query.router)
app.include_router(update.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# MCP server mounted at /mcp
from app.mcp.server import mcp  # noqa: E402

mcp_app = mcp.streamable_http_app()
app.mount("/mcp", mcp_app)
