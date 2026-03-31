"""Tests for the code chunking logic in embedding.py."""

import tempfile
from pathlib import Path

import pytest

from app.services.embedding import chunk_repository, Chunk, CHUNK_MAX_CHARS


@pytest.fixture
def repo_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestChunkRepository:
    def test_readme_is_single_chunk(self, repo_dir):
        (repo_dir / "README.md").write_text("# Hello\n\nThis is a readme with some content.")
        chunks = chunk_repository(repo_dir, "org/repo")
        readme_chunks = [c for c in chunks if c.chunk_type == "readme"]
        assert len(readme_chunks) == 1
        assert "org/repo/README.md" in readme_chunks[0].content
        assert "Hello" in readme_chunks[0].content

    def test_code_file_chunked(self, repo_dir):
        (repo_dir / "main.py").write_text("def foo():\n    pass\n\ndef bar():\n    pass\n")
        chunks = chunk_repository(repo_dir, "org/repo")
        code_chunks = [c for c in chunks if c.chunk_type == "code"]
        assert len(code_chunks) >= 1
        assert code_chunks[0].language == "python"
        assert "org/repo/main.py" in code_chunks[0].content

    def test_large_file_splits(self, repo_dir):
        # Create a file larger than CHUNK_MAX_CHARS
        blocks = ["def func_%d():\n    pass\n" % i for i in range(200)]
        (repo_dir / "big.py").write_text("\n\n".join(blocks))
        chunks = chunk_repository(repo_dir, "org/repo")
        code_chunks = [c for c in chunks if c.file_path == "big.py"]
        assert len(code_chunks) > 1
        for chunk in code_chunks:
            # Each chunk should have the file header
            assert "org/repo/big.py" in chunk.content

    def test_skips_binary_files(self, repo_dir):
        (repo_dir / "image.png").write_bytes(b"\x89PNG\r\n")
        (repo_dir / "main.py").write_text("pass")
        chunks = chunk_repository(repo_dir, "org/repo")
        assert not any(c.file_path == "image.png" for c in chunks)

    def test_skips_node_modules(self, repo_dir):
        nm = repo_dir / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("module.exports = {}")
        (repo_dir / "app.js").write_text("console.log('hi')")
        chunks = chunk_repository(repo_dir, "org/repo")
        assert not any("node_modules" in c.file_path for c in chunks)
        assert any(c.file_path == "app.js" for c in chunks)

    def test_skips_large_files(self, repo_dir):
        (repo_dir / "huge.py").write_text("x" * 200_000)
        chunks = chunk_repository(repo_dir, "org/repo")
        assert not any(c.file_path == "huge.py" for c in chunks)

    def test_config_file_single_chunk(self, repo_dir):
        (repo_dir / "Dockerfile").write_text("FROM python:3.12\nRUN pip install foo\nCMD ['python', 'app.py']")
        chunks = chunk_repository(repo_dir, "org/repo")
        docker_chunks = [c for c in chunks if c.file_path == "Dockerfile"]
        assert len(docker_chunks) == 1
        assert docker_chunks[0].chunk_type == "config"

    def test_empty_file_skipped(self, repo_dir):
        (repo_dir / "empty.py").write_text("")
        (repo_dir / "notempty.py").write_text("x = 1")
        chunks = chunk_repository(repo_dir, "org/repo")
        assert not any(c.file_path == "empty.py" for c in chunks)
        assert any(c.file_path == "notempty.py" for c in chunks)

    def test_language_detection(self, repo_dir):
        (repo_dir / "app.ts").write_text("const x: number = 1;")
        (repo_dir / "style.css").write_text("body { margin: 0; }")
        (repo_dir / "main.go").write_text("package main")
        chunks = chunk_repository(repo_dir, "org/repo")
        langs = {c.file_path: c.language for c in chunks}
        assert langs["app.ts"] == "typescript"
        assert langs["style.css"] == "css"
        assert langs["main.go"] == "go"


class TestChunkContent:
    def test_chunk_has_file_header(self, repo_dir):
        (repo_dir / "utils.py").write_text("def helper(): return 42")
        chunks = chunk_repository(repo_dir, "myorg/myrepo")
        assert any("# file: myorg/myrepo/utils.py" in c.content for c in chunks)

    def test_no_chunk_exceeds_max_by_much(self, repo_dir):
        # Chunks can be slightly over due to headers, but shouldn't be wildly over
        blocks = ["# block %d\n%s\n" % (i, "x" * 100) for i in range(100)]
        (repo_dir / "big.py").write_text("\n\n".join(blocks))
        chunks = chunk_repository(repo_dir, "org/repo")
        for chunk in chunks:
            # Allow 2x max for header + overlap tolerance
            assert len(chunk.content) < CHUNK_MAX_CHARS * 5, f"Chunk too large: {len(chunk.content)} chars"
