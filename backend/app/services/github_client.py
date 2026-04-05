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


async def get_authenticated_user(token: str) -> str:
    """Returns the login (username) of the authenticated token owner."""
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get("https://api.github.com/user", headers=headers)
        resp.raise_for_status()
        return resp.json()["login"]


async def list_all_accessible_repos(token: str) -> list[dict]:
    """
    Fetches all repos the token can access via GET /user/repos with pagination.
    affiliation covers owned, collaborator, and org-member repos.
    Returns raw dicts with at minimum: full_name, description, language, private, html_url.
    """
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    repos = []
    url = "https://api.github.com/user/repos"
    params: dict = {"per_page": 100, "affiliation": "owner,collaborator,organization_member"}
    async with httpx.AsyncClient(timeout=60) as client:
        while url:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            repos.extend(resp.json())
            # GitHub pagination via Link header
            link = resp.headers.get("Link", "")
            next_url = None
            for part in link.split(","):
                if 'rel="next"' in part:
                    next_url = part.split(";")[0].strip().strip("<>")
            url = next_url
            params = {}  # params are encoded in next_url
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
