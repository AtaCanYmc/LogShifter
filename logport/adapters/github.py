import asyncio
import base64
import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List
from logport.core.adapter import TransportAdapter
from logport.core.exceptions import AdapterError

logger = logging.getLogger("logport.adapters.github")


class GitHubAdapter(TransportAdapter):
    """
    GitHubAdapter commits and pushes log files directly to a GitHub Repository
    using the GitHub Contents API.
    
    Required Config:
        - token (or LOGPORT_GITHUB_TOKEN env): GitHub Personal Access Token
    """

    def __init__(self, name: str = "github", config: Dict[str, Any] | None = None) -> None:
        super().__init__(name, config)
        self.token = self.config.get("token") or self.config.get("LOGPORT_GITHUB_TOKEN")

    async def ship(self, logs: List[Dict[str, Any]], target: str, **kwargs: Any) -> bool:
        """
        Ships logs to a GitHub repository contents.
        
        Args:
            logs: List of log dictionaries to be serialized as JSON/YAML.
            target: The repository path in the format "owner/repo".
            **kwargs: 
                - path: The file path within the repo (default: "logs/archive.json").
                - message: Commit message (default: "chore: archive logs [logport]").
                - branch: Branch name (default: "main").
        """
        if not self.token:
            raise AdapterError("GitHub Personal Access Token is missing from configuration.")

        if "/" not in target:
            raise AdapterError("Target must be in the format 'owner/repo'.")

        path = kwargs.get("path", "logs/archive.json")
        commit_message = kwargs.get("message", "chore: archive logs [logport]")
        branch = kwargs.get("branch", "main")

        # Format logs as pretty JSON
        content_str = json.dumps(logs, indent=2, ensure_ascii=False)
        content_bytes = content_str.encode("utf-8")
        content_b64 = base64.b64encode(content_bytes).decode("utf-8")

        url = f"https://api.github.com/repos/{target}/contents/{path}"

        # Run API calls in synchronous executor using asyncio.to_thread to keep it async
        return await asyncio.to_thread(
            self._execute_github_push, url, content_b64, commit_message, branch
        )

    def _execute_github_push(self, url: str, content_b64: str, message: str, branch: str) -> bool:
        # Get existing file sha if it exists
        sha = self._get_existing_file_sha(url, branch)

        payload = {
            "message": message,
            "content": content_b64,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "User-Agent": "logport-sdk",
            },
            method="PUT",
        )

        try:
            with urllib.request.urlopen(req) as response:
                if response.status in (200, 201):
                    logger.info(f"Successfully committed logs to GitHub: {url}")
                    return True
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.error(f"GitHub API Error details: {error_body}")
            raise AdapterError(f"GitHub API returned HTTP {e.code}: {e.reason}") from e
        except Exception as e:
            raise AdapterError(f"Failed to push to GitHub: {e}") from e

        return False

    def _get_existing_file_sha(self, url: str, branch: str) -> str | None:
        """Fetch current file SHA if file already exists in repository."""
        get_url = f"{url}?ref={branch}"
        req = urllib.request.Request(
            get_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "logport-sdk",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    return data.get("sha")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # File doesn't exist yet, this is expected for the first run
                return None
            logger.warning(f"Error checking file SHA (HTTP {e.code}): {e.reason}")
        except Exception as e:
            logger.warning(f"Error checking file SHA: {e}")
        return None
