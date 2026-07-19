from unittest.mock import MagicMock, mock_open, patch

import pytest

from logshift.adapters.github import GitHubAdapter


@pytest.mark.asyncio
async def test_github_adapter_dry_run():
    adapter = GitHubAdapter(token="mock-token")
    # Dry run should return True without executing git
    res = await adapter.ship(logs=[{"id": 1, "message": "hello"}], target="user/repo", dry_run=True)
    assert res is True


@pytest.mark.asyncio
@patch("git.Repo")
async def test_github_adapter_real_flow(mock_repo_cls):
    # Mocking clone and git repository objects
    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = True
    mock_repo.untracked_files = ["logs/archive.json"]
    mock_repo_cls.clone_from.return_value = mock_repo

    adapter = GitHubAdapter(token="mock-token")

    with patch("builtins.open", mock_open()), patch("os.path.exists", return_value=False):
        res = await adapter.ship(
            logs=[{"id": 1, "message": "hello"}], target="user/repo", dry_run=False
        )
        assert res is True

    mock_repo_cls.clone_from.assert_called_once()
    mock_repo.index.add.assert_called_once_with(["logs/archive.json"])
    mock_repo.index.commit.assert_called_once()
    mock_repo.remotes.origin.push.assert_called_once()
    assert adapter.token == "mock-token"
