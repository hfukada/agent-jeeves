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


class GitHubClient:
    def __init__(self, token: str, client: httpx.AsyncClient | None = None) -> None:
        self._token = token
        self._client = client if client is not None else httpx.AsyncClient(timeout=60)

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_authenticated_user(self) -> str:
        """Returns the login (username) of the authenticated token owner."""
        resp = await self._client.get(
            "https://api.github.com/user",
            headers=self._headers,
        )
        resp.raise_for_status()
        return resp.json()["login"]

    async def list_all_accessible_repos(self) -> list[dict]:
        """
        Fetches all repos the token can access via GET /user/repos with pagination.
        affiliation covers owned, collaborator, and org-member repos.
        Returns raw dicts with at minimum: full_name, description, language, private, html_url.
        """
        repos: list[dict] = []
        url: str | None = "https://api.github.com/user/repos"
        params: dict = {"per_page": 100, "affiliation": "owner,collaborator,organization_member"}

        while url:
            resp = await self._client.get(url, headers=self._headers, params=params)
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

    async def list_repos(self, org: str) -> list[RepoInfo]:
        """List all repositories for an organization or user."""
        # Try org endpoint first, fall back to user endpoint
        last_resp = None
        for endpoint in [f"/orgs/{org}/repos", f"/users/{org}/repos"]:
            resp = await self._client.get(
                f"https://api.github.com{endpoint}",
                params={"per_page": 100},
                headers=self._headers,
            )
            last_resp = resp
            if resp.status_code == 200:
                break
        else:
            last_resp.raise_for_status()

        data = resp.json()
        return [
            RepoInfo(
                full_name=r["full_name"],
                clone_url=r["clone_url"],
                default_branch=r.get("default_branch", "main"),
                description=r.get("description"),
                private=r["private"],
            )
            for r in data
        ]

    async def clone_repo(self, clone_url: str, dest: Path | None = None) -> Path:
        """Shallow clone a repository. Returns the path to the cloned directory."""
        if dest is None:
            dest = Path(tempfile.mkdtemp(prefix="jeeves_"))

        # Inject token into clone URL for private repos
        authed_url = clone_url.replace("https://", f"https://x-access-token:{self._token}@")

        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth", "1", "--single-branch", authed_url, str(dest),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"git clone failed: {stderr.decode()}")

        return dest


# Module-level shims preserving existing call signatures

async def list_repos(org: str, token: str) -> list[RepoInfo]:
    return await GitHubClient(token).list_repos(org)


async def get_authenticated_user(token: str) -> str:
    return await GitHubClient(token).get_authenticated_user()


async def list_all_accessible_repos(token: str) -> list[dict]:
    return await GitHubClient(token).list_all_accessible_repos()


async def clone_repo(clone_url: str, token: str, dest: Path | None = None) -> Path:
    return await GitHubClient(token).clone_repo(clone_url, dest)
