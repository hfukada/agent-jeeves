import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass
class RepoInfo:
    full_name: str
    clone_url: str
    default_branch: str
    description: str | None
    private: bool


async def list_repos(org: str, token: str) -> list[RepoInfo]:
    """List all repositories for an organization or user."""
    repos: list[RepoInfo] = []
    page = 1

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            # Try org endpoint first, fall back to user endpoint
            for endpoint in [f"/orgs/{org}/repos", f"/users/{org}/repos"]:
                resp = await client.get(
                    f"https://api.github.com{endpoint}",
                    params={"per_page": 100, "page": page},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )
                if resp.status_code == 200:
                    break
            else:
                resp.raise_for_status()

            data = resp.json()
            if not data:
                break

            for r in data:
                repos.append(
                    RepoInfo(
                        full_name=r["full_name"],
                        clone_url=r["clone_url"],
                        default_branch=r.get("default_branch", "main"),
                        description=r.get("description"),
                        private=r["private"],
                    )
                )

            if len(data) < 100:
                break
            page += 1

    return repos


async def clone_repo(clone_url: str, token: str, dest: Path | None = None) -> Path:
    """Shallow clone a repository. Returns the path to the cloned directory."""
    if dest is None:
        dest = Path(tempfile.mkdtemp(prefix="jeeves_"))

    # Inject token into clone URL for private repos
    authed_url = clone_url.replace("https://", f"https://x-access-token:{token}@")

    proc = await asyncio.create_subprocess_exec(
        "git", "clone", "--depth", "1", "--single-branch", authed_url, str(dest),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"git clone failed: {stderr.decode()}")

    return dest
