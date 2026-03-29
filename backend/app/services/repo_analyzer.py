import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RepoAnalysis:
    summary: str = ""
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    deployment_pattern: str | None = None
    test_commands: list[str] = field(default_factory=list)
    lint_commands: list[str] = field(default_factory=list)
    docker_build: str | None = None


# Maps dependency names to framework display names
FRAMEWORK_MAP = {
    # Python
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "starlette": "Starlette",
    "celery": "Celery",
    "sqlalchemy": "SQLAlchemy",
    "pydantic": "Pydantic",
    "pytest": "pytest",
    # JavaScript/TypeScript
    "react": "React",
    "next": "Next.js",
    "vue": "Vue",
    "nuxt": "Nuxt",
    "svelte": "Svelte",
    "@sveltejs/kit": "SvelteKit",
    "express": "Express",
    "hono": "Hono",
    "tailwindcss": "Tailwind CSS",
    "typescript": "TypeScript",
    # Go
    "gin-gonic/gin": "Gin",
    "labstack/echo": "Echo",
    "gorilla/mux": "Gorilla Mux",
    # Ruby
    "rails": "Ruby on Rails",
    "sinatra": "Sinatra",
    # Java
    "spring-boot": "Spring Boot",
    # Rust
    "actix-web": "Actix Web",
    "axum": "Axum",
    "tokio": "Tokio",
}

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".java": "Java",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C",
    ".hpp": "C++",
    ".cs": "C#",
    ".php": "PHP",
    ".scala": "Scala",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".hs": "Haskell",
    ".lua": "Lua",
    ".r": "R",
    ".R": "R",
    ".dart": "Dart",
    ".zig": "Zig",
    ".nim": "Nim",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
}

SKIP_DIRS = {
    ".git", "node_modules", "vendor", "venv", ".venv", "__pycache__",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build", ".next",
    ".svelte-kit", "target", "bin", "obj",
}


def analyze_repo(repo_path: Path) -> RepoAnalysis:
    result = RepoAnalysis()
    result.summary = _extract_summary(repo_path)
    result.languages = _detect_languages(repo_path)
    result.frameworks = _detect_frameworks(repo_path)
    result.deployment_pattern = _detect_deployment(repo_path)
    result.test_commands = _detect_test_commands(repo_path)
    result.lint_commands = _detect_lint_commands(repo_path)
    result.docker_build = _detect_docker_build(repo_path)
    return result


def _extract_summary(repo_path: Path) -> str:
    for name in ["README.md", "README.rst", "README.txt", "README"]:
        readme = repo_path / name
        if readme.is_file():
            text = readme.read_text(errors="replace")
            # Take first 500 words
            words = text.split()[:500]
            return " ".join(words)
    return ""


def _detect_languages(repo_path: Path) -> list[str]:
    counts: dict[str, int] = {}
    for path in _walk_files(repo_path):
        ext = path.suffix.lower()
        lang = LANGUAGE_EXTENSIONS.get(ext)
        if lang:
            counts[lang] = counts.get(lang, 0) + 1

    # Sort by file count, return top languages
    sorted_langs = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [lang for lang, _ in sorted_langs[:10]]


def _detect_frameworks(repo_path: Path) -> list[str]:
    frameworks: set[str] = set()

    # Check package.json
    pkg_json = repo_path / "package.json"
    if pkg_json.is_file():
        try:
            data = json.loads(pkg_json.read_text(errors="replace"))
            all_deps = {}
            all_deps.update(data.get("dependencies", {}))
            all_deps.update(data.get("devDependencies", {}))
            for dep in all_deps:
                if dep in FRAMEWORK_MAP:
                    frameworks.add(FRAMEWORK_MAP[dep])
        except (json.JSONDecodeError, KeyError):
            pass

    # Check pyproject.toml (simple parsing)
    pyproject = repo_path / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(errors="replace").lower()
        for dep, name in FRAMEWORK_MAP.items():
            if dep in text:
                frameworks.add(name)

    # Check requirements.txt
    for req_file in ["requirements.txt", "requirements-dev.txt"]:
        req = repo_path / req_file
        if req.is_file():
            text = req.read_text(errors="replace").lower()
            for dep, name in FRAMEWORK_MAP.items():
                if dep in text:
                    frameworks.add(name)

    # Check go.mod
    gomod = repo_path / "go.mod"
    if gomod.is_file():
        text = gomod.read_text(errors="replace")
        for dep, name in FRAMEWORK_MAP.items():
            if dep in text:
                frameworks.add(name)

    # Check Gemfile
    gemfile = repo_path / "Gemfile"
    if gemfile.is_file():
        text = gemfile.read_text(errors="replace").lower()
        for dep, name in FRAMEWORK_MAP.items():
            if dep in text:
                frameworks.add(name)

    # Check build.gradle / pom.xml
    for build_file in ["build.gradle", "build.gradle.kts", "pom.xml"]:
        bf = repo_path / build_file
        if bf.is_file():
            text = bf.read_text(errors="replace").lower()
            for dep, name in FRAMEWORK_MAP.items():
                if dep in text:
                    frameworks.add(name)

    # Check Cargo.toml
    cargo = repo_path / "Cargo.toml"
    if cargo.is_file():
        text = cargo.read_text(errors="replace").lower()
        for dep, name in FRAMEWORK_MAP.items():
            if dep in text:
                frameworks.add(name)

    return sorted(frameworks)


def _detect_deployment(repo_path: Path) -> str | None:
    # Check in order of specificity
    if (repo_path / "kubernetes").is_dir() or (repo_path / "k8s").is_dir():
        return "kubernetes"
    if any((repo_path / f).is_file() for f in ["chart.yaml", "Chart.yaml"]):
        return "helm"
    if (repo_path / "terraform").is_dir() or list(repo_path.glob("*.tf")):
        return "terraform"
    if (repo_path / "serverless.yml").is_file() or (repo_path / "serverless.yaml").is_file():
        return "serverless"
    if (repo_path / "Procfile").is_file():
        return "heroku"
    if (repo_path / "fly.toml").is_file():
        return "fly.io"
    if (repo_path / "render.yaml").is_file():
        return "render"
    if (repo_path / "docker-compose.yml").is_file() or (repo_path / "docker-compose.yaml").is_file():
        return "docker-compose"
    if (repo_path / "Dockerfile").is_file():
        return "docker"
    # Check for CI/CD deployment steps
    gh_workflows = repo_path / ".github" / "workflows"
    if gh_workflows.is_dir():
        return "github-actions"
    if (repo_path / ".gitlab-ci.yml").is_file():
        return "gitlab-ci"
    return None


def _detect_test_commands(repo_path: Path) -> list[str]:
    commands: list[str] = []

    # package.json scripts
    pkg = repo_path / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(errors="replace"))
            scripts = data.get("scripts", {})
            for key in ["test", "test:unit", "test:e2e", "test:integration"]:
                if key in scripts:
                    commands.append(f"npm run {key}")
        except (json.JSONDecodeError, KeyError):
            pass

    # Python
    if (repo_path / "pyproject.toml").is_file() or (repo_path / "pytest.ini").is_file() or (repo_path / "setup.cfg").is_file():
        if any(_walk_files(repo_path, match_prefix="test_", limit=1)):
            commands.append("pytest")

    # Makefile
    makefile = repo_path / "Makefile"
    if makefile.is_file():
        text = makefile.read_text(errors="replace")
        for line in text.splitlines():
            if line.startswith("test") and ":" in line:
                target = line.split(":")[0].strip()
                commands.append(f"make {target}")

    # Go
    if (repo_path / "go.mod").is_file():
        commands.append("go test ./...")

    return commands


def _detect_lint_commands(repo_path: Path) -> list[str]:
    commands: list[str] = []

    # package.json
    pkg = repo_path / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(errors="replace"))
            scripts = data.get("scripts", {})
            for key in ["lint", "lint:fix"]:
                if key in scripts:
                    commands.append(f"npm run {key}")
        except (json.JSONDecodeError, KeyError):
            pass

    # Python linters
    if (repo_path / "ruff.toml").is_file() or (repo_path / ".ruff.toml").is_file():
        commands.append("ruff check .")
    elif (repo_path / "pyproject.toml").is_file():
        text = (repo_path / "pyproject.toml").read_text(errors="replace")
        if "[tool.ruff" in text:
            commands.append("ruff check .")
        if "[tool.black" in text or "[tool.blue" in text:
            commands.append("black --check .")
    if (repo_path / ".flake8").is_file() or (repo_path / "setup.cfg").is_file():
        commands.append("flake8")

    # ESLint
    for name in [".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.cjs", "eslint.config.js", "eslint.config.mjs"]:
        if (repo_path / name).is_file():
            if not any("lint" in c for c in commands):
                commands.append("eslint .")
            break

    # Go
    if (repo_path / "go.mod").is_file():
        commands.append("golangci-lint run")

    # Makefile
    makefile = repo_path / "Makefile"
    if makefile.is_file():
        text = makefile.read_text(errors="replace")
        for line in text.splitlines():
            if line.startswith("lint") and ":" in line:
                target = line.split(":")[0].strip()
                commands.append(f"make {target}")

    return commands


def _detect_docker_build(repo_path: Path) -> str | None:
    dockerfile = repo_path / "Dockerfile"
    if not dockerfile.is_file():
        return None

    # Check docker-compose for build context
    for compose_name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
        compose = repo_path / compose_name
        if compose.is_file():
            return f"docker compose build"

    return "docker build -t <image> ."


def _walk_files(repo_path: Path, match_prefix: str | None = None, limit: int | None = None) -> list[Path]:
    """Walk repo files, skipping common non-source directories."""
    results: list[Path] = []
    count = 0
    for item in repo_path.rglob("*"):
        if any(part in SKIP_DIRS for part in item.parts):
            continue
        if item.is_file():
            if match_prefix and not item.name.startswith(match_prefix):
                continue
            results.append(item)
            count += 1
            if limit and count >= limit:
                break
    return results
