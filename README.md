# Agent Jeeves

Code knowledge base for multi-repository organizations. Index your GitHub org's repositories and search across them using semantic search.

## What it does

Given a GitHub token and an organization/username, Agent Jeeves will:

- Clone and analyze each repository
- Extract metadata: languages, frameworks, deployment patterns, test/lint/build commands
- Generate embeddings for semantic code search using Ollama (nomic-embed-text)
- Expose an HTTP API and MCP server for querying
- Provide a chat-style web frontend for searching

## Architecture

- **Backend**: Python / FastAPI
- **Frontend**: SvelteKit
- **Database**: PostgreSQL (structured data), ChromaDB (embeddings)
- **Embeddings**: Ollama with nomic-embed-text
- **Infrastructure**: Docker Compose

## Quick Start

1. Copy the environment file and set your GitHub token:

```bash
cp .env.example .env
# Edit .env and set GITHUB_TOKEN=ghp_...
```

2. Start all services:

```bash
docker compose up --build
```

3. Register your organization and trigger indexing:

```bash
# Register org
curl -X POST http://localhost:8080/api/orgs \
  -H 'Content-Type: application/json' \
  -d '{"name": "your-org", "github_token": "ghp_..."}'

# Trigger indexing (use the org_id from the response)
curl -X POST http://localhost:8080/api/orgs/<org_id>/index

# Poll job status
curl http://localhost:8080/api/jobs/<job_id>
```

4. Search via the frontend at http://localhost:3000 or via API:

```bash
# Submit a query
curl -X POST http://localhost:8080/api/query \
  -H 'Content-Type: application/json' \
  -d '{"question": "Which repos use authentication?"}'

# Get the answer (use the query_id from the response)
curl http://localhost:8080/api/query/<query_id>
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/orgs | Register an organization |
| POST | /api/orgs/{id}/index | Trigger repository indexing |
| GET | /api/jobs/{id} | Poll indexing job status |
| GET | /api/orgs/{id}/repos | List indexed repositories |
| GET | /api/repos/{id} | Get repository metadata |
| POST | /api/query | Submit a search query |
| GET | /api/query/{id} | Get query results |
| PATCH | /api/repos/{id} | Update repository metadata manually |

## MCP Server

The MCP server is available at `http://localhost:8080/mcp` and exposes:

- `search_code` - Semantic search across repositories
- `get_repo_info` - Get structured metadata for a repo
- `list_repos` - List all repos for an org
- `ask` - High-level question answering

## Development

Backend only (requires PostgreSQL, ChromaDB, Ollama running locally):

```bash
cd backend
pip install -e .
uvicorn app.main:app --reload --port 8080
```

Frontend only:

```bash
cd frontend
npm install
npm run dev
```
