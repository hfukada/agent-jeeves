# Agent Jeeves

Code knowledge base for multi-repository organizations. Indexes GitHub orgs/users, extracts repo metadata, generates embeddings, and exposes HTTP + MCP APIs with a chat frontend.

## Stack

- **Backend**: Python 3.12+ / FastAPI (async) -- `backend/`
- **Frontend**: SvelteKit 5 / TypeScript -- `frontend/`
- **Database**: PostgreSQL 16 (structured data), ChromaDB 0.6 (vector embeddings)
- **Embeddings**: Ollama with `nomic-embed-text`
- **Infra**: Docker Compose (`docker-compose.yml`)

## Running

```bash
cp .env.example .env   # set GITHUB_TOKEN
docker compose up --build
```

- Backend: http://localhost:8080
- Frontend: http://localhost:3000
- MCP: http://localhost:8080/mcp
- ChromaDB exposed on host port 8100 (internal 8000)

## Backend dev (without Docker)

```bash
cd backend
pip install -e .
uvicorn app.main:app --reload --port 8080
```

Requires local PostgreSQL, ChromaDB, and Ollama running at the defaults in `.env.example`.

## Project layout

```
backend/
  app/
    main.py           -- FastAPI app, lifespan, router mounting, MCP mount
    config.py         -- pydantic-settings (env vars: DATABASE_URL, CHROMA_HOST, CHROMA_PORT, OLLAMA_BASE_URL, GITHUB_TOKEN)
    db.py             -- async SQLAlchemy engine + session factory
    models.py         -- ORM: Organization, Repository, Query, IndexingJob
    schemas.py        -- Pydantic request/response models
    routers/
      indexing.py     -- POST /api/orgs, POST /api/orgs/{id}/index, GET /api/jobs/{id}, GET /api/orgs/{id}/repos, GET /api/repos/{id}
      query.py        -- POST /api/query, GET /api/query/{id}
      update.py       -- PATCH /api/repos/{id}
    services/
      github_client.py   -- list_repos(), clone_repo() via GitHub API + git CLI
      repo_analyzer.py   -- analyze_repo() heuristics for languages, frameworks, deployment, test/lint/build
      embedding.py       -- chunk_repository(), embed_text(), store_chunks() via Ollama + ChromaDB
      query_engine.py    -- process_query() async pipeline: embed -> ChromaDB search -> compose answer
      background.py      -- run_indexing_job() orchestrates clone/analyze/embed per repo
    mcp/
      server.py       -- FastMCP tools: search_code, get_repo_info, list_repos, ask
  alembic/            -- DB migrations (current head: 001)
frontend/
  src/
    lib/api.ts        -- submitQuery(), pollQuery() API client
    lib/components/   -- ChatInput.svelte, ChatMessage.svelte
    routes/           -- +layout.svelte, +page.svelte (chat UI)
```

## Database

4 PostgreSQL tables: `organizations`, `repositories`, `queries`, `indexing_jobs`.
1 ChromaDB collection: `code_chunks` (metadata: repo_id, file_path, language, chunk_type).
Alembic manages migrations from `backend/alembic/`.

## Async query pattern

POST /api/query returns a query_id immediately. Background asyncio task embeds the question, searches ChromaDB, composes the answer, and updates the row. Client polls GET /api/query/{id} until status is `done` or `error`.

## Conventions

- All backend async (asyncpg, httpx, asyncio subprocesses for git)
- UUIDs for all primary keys
- JSONB columns for list-type metadata (languages, frameworks, commands, sources)
- GitHub tokens are bcrypt-hashed in DB; runtime token comes from GITHUB_TOKEN env var
- ChromaDB cosine similarity; chunks prefixed with `# file: org/repo/path` for context
- Code chunking: README/config as whole files, source code split at blank-line boundaries (~2000 chars per chunk)
