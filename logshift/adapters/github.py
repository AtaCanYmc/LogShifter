import os
import json
import logging
import shutil
import tempfile
from typing import Any, Dict, List
from logshift.core.adapter import TransportAdapter
from logshift.core.exceptions import AdapterError

logger = logging.getLogger("logshift.adapters.github")


class GitHubAdapter(TransportAdapter):
    """
    GitHubAdapter writes log data into a JSON file, commits and pushes 
    changes to a GitHub Repository using GitPython.
    """

    def __init__(self, token: str, name: str = "github", config: Dict[str, Any] | None = None) -> None:
        """
        Args:
            token: GitHub Personal Access Token.
            name: Name of the adapter instance.
            config: Optional config dict.
        """
        super().__init__(name, config)
        self.token = token

    async def ship(self, logs: List[Dict[str, Any]], target: str, **kwargs: Any) -> bool:
        """
        Ships logs by cloning repository, writing JSON file, committing and pushing.
        
        Args:
            logs: List of log dictionaries.
            target: GitHub repository in the format "owner/repo".
            **kwargs:
                - path: Relative path inside the repo (default: "logs/archive.json").
                - message: Commit message.
                - branch: Branch name (default: "main").
        """
        # Defer import to avoid GitPython import overhead when not using it
        import git

        if not self.token:
            raise AdapterError("GitHub Personal Access Token is required.")

        if "/" not in target:
            raise AdapterError("Target must be in the format 'owner/repo'.")

        path = kwargs.get("path", "logs/archive.json")
        commit_message = kwargs.get("message", "Archive logs")
        branch = kwargs.get("branch", "main")

        # Format URL with token for HTTP authentication
        repo_url = f"https://x-access-token:{self.token}@github.com/{target}.git"

        # Create a temp directory for cloning
        temp_dir = tempfile.mkdtemp()
        try:
            logger.info(f"Cloning repository {target} to temporary folder...")
            # Clone repo
            repo = git.Repo.clone_from(repo_url, temp_dir, branch=branch)

            # Target log file path
            file_abs_path = os.path.join(temp_dir, path)
            os.makedirs(os.path.dirname(file_abs_path), exist_ok=True)

            # Load existing logs or initialize new list
            existing_logs: List[Dict[str, Any]] = []
            if os.path.exists(file_abs_path):
                try:
                    with open(file_abs_path, "r", encoding="utf-8") as f:
                        existing_logs = json.load(f)
                        if not isinstance(existing_logs, list):
                            existing_logs = [existing_logs]
                except Exception as e:
                    logger.warning(f"Failed to read existing log file, starting fresh: {e}")

            # Append new logs
            existing_logs.extend(logs)

            # Save file back
            with open(file_abs_path, "w", encoding="utf-8") as f:
                json.dump(existing_logs, f, indent=2, ensure_ascii=False)

            # Check if there are changes
            if not repo.is_dirty() and not repo.untracked_files:
                logger.info("No new log changes detected. Repository is up-to-date.")
                return True

            # Git add
            repo.index.add([path])

            # Git commit
            repo.index.commit(commit_message)

            # Git push
            logger.info("Pushing committed logs to remote...")
            repo.remotes.origin.push()
            logger.info("Successfully pushed logs to GitHub.")
            return True

        except git.exc.GitCommandError as e:
            # Mask the token in errors if it's in the command output
            err_msg = str(e).replace(self.token, "********")
            raise AdapterError(f"Git command failed: {err_msg}") from e
        except Exception as e:
            raise AdapterError(f"Failed to push logs to GitHub: {e}") from e
        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
