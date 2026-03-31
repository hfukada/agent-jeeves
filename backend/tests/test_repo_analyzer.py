"""Tests for repo_analyzer heuristics."""

import json
import tempfile
from pathlib import Path

import pytest

from app.services.repo_analyzer import analyze_repo, RepoAnalysis


@pytest.fixture
def repo_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestExtractSummary:
    def test_readme_extracted(self, repo_dir):
        (repo_dir / "README.md").write_text("# My Project\n\nThis is a great project for doing things.")
        result = analyze_repo(repo_dir)
        assert "great project" in result.summary

    def test_no_readme(self, repo_dir):
        (repo_dir / "main.py").write_text("print('hello')")
        result = analyze_repo(repo_dir)
        assert result.summary == ""

    def test_readme_rst(self, repo_dir):
        (repo_dir / "README.rst").write_text("My Project\n==========\nRST readme content.")
        result = analyze_repo(repo_dir)
        assert "RST readme" in result.summary


class TestDetectLanguages:
    def test_python_files(self, repo_dir):
        (repo_dir / "main.py").write_text("print('hi')")
        (repo_dir / "utils.py").write_text("def foo(): pass")
        result = analyze_repo(repo_dir)
        assert "Python" in result.languages

    def test_multiple_languages(self, repo_dir):
        (repo_dir / "app.py").write_text("pass")
        (repo_dir / "index.js").write_text("console.log('hi')")
        (repo_dir / "main.go").write_text("package main")
        result = analyze_repo(repo_dir)
        assert "Python" in result.languages
        assert "JavaScript" in result.languages
        assert "Go" in result.languages

    def test_skips_node_modules(self, repo_dir):
        nm = repo_dir / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("module.exports = {}")
        (repo_dir / "app.py").write_text("pass")
        result = analyze_repo(repo_dir)
        assert "JavaScript" not in result.languages
        assert "Python" in result.languages


class TestDetectFrameworks:
    def test_package_json_react(self, repo_dir):
        (repo_dir / "package.json").write_text(json.dumps({
            "dependencies": {"react": "^18.0.0"},
            "devDependencies": {"typescript": "^5.0.0"},
        }))
        result = analyze_repo(repo_dir)
        assert "React" in result.frameworks
        assert "TypeScript" in result.frameworks

    def test_pyproject_fastapi(self, repo_dir):
        (repo_dir / "pyproject.toml").write_text('[project]\ndependencies = ["fastapi", "sqlalchemy"]')
        result = analyze_repo(repo_dir)
        assert "FastAPI" in result.frameworks
        assert "SQLAlchemy" in result.frameworks

    def test_requirements_txt(self, repo_dir):
        (repo_dir / "requirements.txt").write_text("flask>=2.0\npydantic\n")
        result = analyze_repo(repo_dir)
        assert "Flask" in result.frameworks
        assert "Pydantic" in result.frameworks

    def test_go_mod(self, repo_dir):
        (repo_dir / "go.mod").write_text("module myapp\nrequire github.com/gin-gonic/gin v1.9.0\n")
        result = analyze_repo(repo_dir)
        assert "Gin" in result.frameworks

    def test_cargo_toml(self, repo_dir):
        (repo_dir / "Cargo.toml").write_text('[dependencies]\naxum = "0.7"\ntokio = "1"\n')
        result = analyze_repo(repo_dir)
        assert "Axum" in result.frameworks
        assert "Tokio" in result.frameworks


class TestDetectDeployment:
    def test_kubernetes_dir(self, repo_dir):
        (repo_dir / "kubernetes").mkdir()
        (repo_dir / "kubernetes" / "deployment.yaml").write_text("kind: Deployment")
        result = analyze_repo(repo_dir)
        assert result.deployment_pattern == "kubernetes"

    def test_dockerfile(self, repo_dir):
        (repo_dir / "Dockerfile").write_text("FROM python:3.12")
        result = analyze_repo(repo_dir)
        assert result.deployment_pattern == "docker"

    def test_docker_compose(self, repo_dir):
        (repo_dir / "docker-compose.yml").write_text("services:\n  app:\n    build: .")
        result = analyze_repo(repo_dir)
        assert result.deployment_pattern == "docker-compose"

    def test_heroku(self, repo_dir):
        (repo_dir / "Procfile").write_text("web: gunicorn app:app")
        result = analyze_repo(repo_dir)
        assert result.deployment_pattern == "heroku"

    def test_terraform(self, repo_dir):
        (repo_dir / "main.tf").write_text('resource "aws_instance" "web" {}')
        result = analyze_repo(repo_dir)
        assert result.deployment_pattern == "terraform"

    def test_no_deployment(self, repo_dir):
        (repo_dir / "main.py").write_text("pass")
        result = analyze_repo(repo_dir)
        assert result.deployment_pattern is None


class TestDetectTestCommands:
    def test_npm_test(self, repo_dir):
        (repo_dir / "package.json").write_text(json.dumps({
            "scripts": {"test": "jest", "test:e2e": "cypress run"}
        }))
        result = analyze_repo(repo_dir)
        assert "npm run test" in result.test_commands
        assert "npm run test:e2e" in result.test_commands

    def test_pytest(self, repo_dir):
        (repo_dir / "pyproject.toml").write_text("[tool.pytest]\n")
        (repo_dir / "test_main.py").write_text("def test_foo(): pass")
        result = analyze_repo(repo_dir)
        assert "pytest" in result.test_commands

    def test_go_test(self, repo_dir):
        (repo_dir / "go.mod").write_text("module myapp")
        result = analyze_repo(repo_dir)
        assert "go test ./..." in result.test_commands

    def test_makefile_test(self, repo_dir):
        (repo_dir / "Makefile").write_text("test:\n\tpytest\n")
        result = analyze_repo(repo_dir)
        assert "make test" in result.test_commands


class TestDetectLintCommands:
    def test_ruff_toml(self, repo_dir):
        (repo_dir / "ruff.toml").write_text("[lint]\n")
        result = analyze_repo(repo_dir)
        assert "ruff check ." in result.lint_commands

    def test_eslint_config(self, repo_dir):
        (repo_dir / "eslint.config.js").write_text("export default []")
        result = analyze_repo(repo_dir)
        assert "eslint ." in result.lint_commands

    def test_npm_lint(self, repo_dir):
        (repo_dir / "package.json").write_text(json.dumps({
            "scripts": {"lint": "eslint src/"}
        }))
        result = analyze_repo(repo_dir)
        assert "npm run lint" in result.lint_commands

    def test_go_lint(self, repo_dir):
        (repo_dir / "go.mod").write_text("module myapp")
        result = analyze_repo(repo_dir)
        assert "golangci-lint run" in result.lint_commands


class TestDetectDockerBuild:
    def test_dockerfile_only(self, repo_dir):
        (repo_dir / "Dockerfile").write_text("FROM node:20")
        result = analyze_repo(repo_dir)
        assert result.docker_build == "docker build -t <image> ."

    def test_with_compose(self, repo_dir):
        (repo_dir / "Dockerfile").write_text("FROM node:20")
        (repo_dir / "docker-compose.yml").write_text("services:\n  app:\n    build: .")
        result = analyze_repo(repo_dir)
        assert result.docker_build == "docker compose build"

    def test_no_dockerfile(self, repo_dir):
        (repo_dir / "main.py").write_text("pass")
        result = analyze_repo(repo_dir)
        assert result.docker_build is None
