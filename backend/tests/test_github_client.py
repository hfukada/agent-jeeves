"""Tests for GitHubClient."""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

from app.services.github_client import GitHubClient, RepoInfo


def make_response(json_data, status_code=200, headers=None, raise_for_status=None):
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.headers = headers or {}
    if raise_for_status is not None:
        resp.raise_for_status.side_effect = raise_for_status
    else:
        resp.raise_for_status = MagicMock()
    return resp


def make_client(responses):
    """Build a mock httpx.AsyncClient whose .get returns responses in sequence."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    if isinstance(responses, list):
        mock_client.get = AsyncMock(side_effect=responses)
    else:
        mock_client.get = AsyncMock(return_value=responses)
    return mock_client


# ---------------------------------------------------------------------------
# get_authenticated_user
# ---------------------------------------------------------------------------

async def test_get_authenticated_user_success():
    resp = make_response({"login": "octocat"})
    client = GitHubClient(token="test-token", client=make_client(resp))
    result = await client.get_authenticated_user()
    assert result == "octocat"
    resp.raise_for_status.assert_called_once()


async def test_get_authenticated_user_401():
    error = httpx.HTTPStatusError(
        "401",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )
    resp = make_response({}, status_code=401, raise_for_status=error)
    client = GitHubClient(token="test-token", client=make_client(resp))
    with pytest.raises(httpx.HTTPStatusError):
        await client.get_authenticated_user()


# ---------------------------------------------------------------------------
# list_all_accessible_repos
# ---------------------------------------------------------------------------

async def test_list_all_accessible_repos_success_no_pagination():
    resp = make_response([{"id": 1}])
    client = GitHubClient(token="test-token", client=make_client(resp))
    result = await client.list_all_accessible_repos()
    assert result == [{"id": 1}]


async def test_list_all_accessible_repos_pagination():
    resp1 = make_response(
        [{"id": 1}],
        headers={"Link": '<https://api.github.com/next>; rel="next"'},
    )
    resp2 = make_response([{"id": 2}])
    client = GitHubClient(token="test-token", client=make_client([resp1, resp2]))
    result = await client.list_all_accessible_repos()
    assert result == [{"id": 1}, {"id": 2}]


async def test_list_all_accessible_repos_401():
    error = httpx.HTTPStatusError(
        "401",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )
    resp = make_response({}, status_code=401, raise_for_status=error)
    client = GitHubClient(token="test-token", client=make_client(resp))
    with pytest.raises(httpx.HTTPStatusError):
        await client.list_all_accessible_repos()


# ---------------------------------------------------------------------------
# list_repos
# ---------------------------------------------------------------------------

_REPO_DICT = {
    "name": "repo1",
    "full_name": "org/repo1",
    "clone_url": "https://github.com/org/repo1.git",
    "html_url": "https://github.com/org/repo1",
    "description": None,
    "language": None,
    "stargazers_count": 0,
    "forks_count": 0,
    "private": False,
    "default_branch": "main",
    "updated_at": "2024-01-01T00:00:00Z",
}


async def test_list_repos_org_endpoint_success():
    resp = make_response([_REPO_DICT], status_code=200)
    client = GitHubClient(token="test-token", client=make_client(resp))
    result = await client.list_repos("org")
    assert len(result) == 1
    assert isinstance(result[0], RepoInfo)
    assert result[0].full_name == "org/repo1"


async def test_list_repos_falls_back_to_user_endpoint():
    resp1 = make_response([], status_code=404)
    resp2 = make_response([_REPO_DICT], status_code=200)
    client = GitHubClient(token="test-token", client=make_client([resp1, resp2]))
    result = await client.list_repos("org")
    assert len(result) == 1
    assert result[0].full_name == "org/repo1"


async def test_list_repos_both_endpoints_fail():
    error = httpx.HTTPStatusError(
        "403",
        request=MagicMock(),
        response=MagicMock(status_code=403),
    )
    resp1 = make_response([], status_code=403, raise_for_status=error)
    resp2 = make_response([], status_code=403, raise_for_status=error)
    client = GitHubClient(token="test-token", client=make_client([resp1, resp2]))
    with pytest.raises(httpx.HTTPStatusError):
        await client.list_repos("org")
