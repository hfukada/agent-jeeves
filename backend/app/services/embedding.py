import logging
from dataclasses import dataclass
from pathlib import Path

import chromadb
import httpx

from app.config import settings
from app.services.repo_analyzer import SKIP_DIRS

logger = logging.getLogger(__name__)

CHUNK_MAX_CHARS = 2000  # ~512 tokens
CHUNK_OVERLAP_CHARS = 200
EMBED_BATCH_SIZE = 32
MAX_FILE_SIZE = 100_000  # 100KB

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".zip", ".gz", ".tar", ".bz2", ".xz", ".7z",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe",
    ".bin", ".dat", ".db", ".sqlite",
    ".mp3", ".mp4", ".avi", ".mov", ".wav",
    ".lock",
}

CONFIG_FILES = {
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "compose.yml", "compose.yaml",
    "Makefile", "Justfile",
    ".github/workflows", ".gitlab-ci.yml",
    "Procfile", "serverless.yml", "fly.toml",
}


@dataclass
class Chunk:
    content: str
    file_path: str
    chunk_type: str  # readme, function, config, code
    language: str


def chunk_repository(repo_path: Path, repo_name: str) -> list[Chunk]:
    """Walk a repository and produce semantic chunks for embedding."""
    chunks: list[Chunk] = []

    for item in repo_path.rglob("*"):
        if not item.is_file():
            continue
        if any(part in SKIP_DIRS for part in item.parts):
            continue
        if item.suffix.lower() in BINARY_EXTENSIONS:
            continue
        if item.stat().st_size > MAX_FILE_SIZE:
            continue

        rel_path = str(item.relative_to(repo_path))

        try:
            text = item.read_text(errors="replace")
        except Exception:
            continue

        if not text.strip():
            continue

        # Determine chunk type and language
        chunk_type = _classify_file(item, rel_path)
        language = _guess_language(item)

        if chunk_type in ("readme", "config"):
            # Keep as single chunk (truncated)
            content = f"# file: {repo_name}/{rel_path}\n\n{text[:CHUNK_MAX_CHARS * 4]}"
            chunks.append(Chunk(content=content, file_path=rel_path, chunk_type=chunk_type, language=language))
        else:
            # Split code into chunks
            file_chunks = _split_code(text, rel_path, repo_name)
            for fc in file_chunks:
                chunks.append(Chunk(content=fc, file_path=rel_path, chunk_type=chunk_type, language=language))

    return chunks


def _classify_file(path: Path, rel_path: str) -> str:
    name_lower = path.name.lower()
    if name_lower.startswith("readme"):
        return "readme"
    if path.name in CONFIG_FILES or any(cf in rel_path for cf in [".github/workflows", ".gitlab-ci"]):
        return "config"
    return "code"


def _guess_language(path: Path) -> str:
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".tsx": "typescript", ".jsx": "javascript", ".go": "go",
        ".rs": "rust", ".rb": "ruby", ".java": "java", ".kt": "kotlin",
        ".c": "c", ".cpp": "cpp", ".cs": "csharp", ".php": "php",
        ".swift": "swift", ".scala": "scala", ".ex": "elixir",
        ".sh": "shell", ".bash": "shell", ".zsh": "shell",
        ".yml": "yaml", ".yaml": "yaml", ".json": "json",
        ".toml": "toml", ".md": "markdown", ".html": "html",
        ".css": "css", ".sql": "sql",
    }
    return ext_map.get(path.suffix.lower(), "unknown")


def _split_code(text: str, rel_path: str, repo_name: str) -> list[str]:
    """Split code into chunks at blank-line boundaries with overlap."""
    header = f"# file: {repo_name}/{rel_path}\n\n"
    chunks: list[str] = []

    # Split by double newlines (paragraph/block boundaries)
    blocks = text.split("\n\n")
    current = header
    for block in blocks:
        if len(current) + len(block) + 2 > CHUNK_MAX_CHARS:
            if current.strip() != header.strip():
                chunks.append(current)
            # Start new chunk with overlap
            overlap = current[-CHUNK_OVERLAP_CHARS:] if len(current) > CHUNK_OVERLAP_CHARS else ""
            current = header + overlap + block
        else:
            current += block + "\n\n"

    if current.strip() != header.strip():
        chunks.append(current)

    # If no splits happened and text is very long, force-split by character
    if not chunks and len(text) > CHUNK_MAX_CHARS:
        for i in range(0, len(text), CHUNK_MAX_CHARS - CHUNK_OVERLAP_CHARS):
            chunk_text = text[i:i + CHUNK_MAX_CHARS]
            chunks.append(header + chunk_text)

    if not chunks:
        chunks.append(header + text)

    return chunks


async def embed_text(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using Ollama nomic-embed-text."""
    all_embeddings: list[list[float]] = []

    async with httpx.AsyncClient(timeout=120) as client:
        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[i:i + EMBED_BATCH_SIZE]
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embed",
                json={"model": "nomic-embed-text", "input": batch},
            )
            resp.raise_for_status()
            data = resp.json()
            all_embeddings.extend(data["embeddings"])

    return all_embeddings


def get_chroma_client() -> chromadb.HttpClient:
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


async def store_chunks(repo_id: str, chunks: list[Chunk]) -> int:
    """Embed chunks and store them in ChromaDB. Returns number of chunks stored."""
    if not chunks:
        return 0

    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name="code_chunks",
        metadata={"hnsw:space": "cosine"},
    )

    # Delete existing chunks for this repo
    try:
        collection.delete(where={"repo_id": repo_id})
    except Exception:
        pass  # Collection might be empty

    texts = [c.content for c in chunks]
    embeddings = await embed_text(texts)

    # Store in batches (ChromaDB has limits)
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i + batch_size]
        batch_embeddings = embeddings[i:i + batch_size]

        collection.add(
            ids=[f"{repo_id}_{i + j}" for j in range(len(batch_chunks))],
            embeddings=batch_embeddings,
            documents=[c.content for c in batch_chunks],
            metadatas=[
                {
                    "repo_id": repo_id,
                    "file_path": c.file_path,
                    "language": c.language,
                    "chunk_type": c.chunk_type,
                }
                for c in batch_chunks
            ],
        )

    logger.info(f"Stored {len(chunks)} chunks for repo {repo_id}")
    return len(chunks)
