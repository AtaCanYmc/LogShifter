import json
import logging
import os
import shutil
import tempfile
from typing import Any, Dict, List

from logshift.core.adapter import TransportAdapter
from logshift.core.exceptions import AdapterError

logger = logging.getLogger("logshift.adapters.github")


class GitHubAdapter(TransportAdapter):
    """
    GitHubAdapter commits and pushes log files directly to a GitHub Repository
    using GitPython, supporting Dry-Run simulation mode.
    """

    def __init__(
        self, token: str, name: str = "github", config: Dict[str, Any] | None = None
    ) -> None:
        super().__init__(name, config)
        self.token = token

    async def ship(self, logs: List[Dict[str, Any]], target: str, **kwargs: Any) -> bool:
        """
        Ships logs using GitPython, support dry-run parameter.
        """
        dry_run = kwargs.get("dry_run", False)
        path = kwargs.get("path", "logs/archive.json")
        commit_message = kwargs.get("message", "Archive logs")
        branch = kwargs.get("branch", "main")

        if dry_run:
            logger.info("---------------- DRY-RUN SIMULATION ----------------")
            logger.info(f"[Dry-Run] Target Repository: {target}")
            logger.info(f"[Dry-Run] Target File Path: {path}")
            logger.info(f"[Dry-Run] Branch: {branch}")
            logger.info(f"[Dry-Run] Commit Message: '{commit_message}'")
            logger.info(f"[Dry-Run] Log Count: {len(logs)}")
            logger.info(f"[Dry-Run] Content Sample: {json.dumps(logs[:2], indent=2)}")
            logger.info("----------------------------------------------------")
            return True

        import git

        if not self.token:
            raise AdapterError("GitHub Personal Access Token is required.")

        if "/" not in target:
            raise AdapterError("Target must be in the format 'owner/repo'.")

        repo_url = f"https://x-access-token:{self.token}@github.com/{target}.git"
        temp_dir = tempfile.mkdtemp()
        try:
            logger.info(f"Cloning repository {target} to temporary folder...")
            repo = git.Repo.clone_from(repo_url, temp_dir, branch=branch)

            file_abs_path = os.path.join(temp_dir, path)
            os.makedirs(os.path.dirname(file_abs_path), exist_ok=True)

            existing_logs: List[Dict[str, Any]] = []
            if os.path.exists(file_abs_path):
                try:
                    with open(file_abs_path, "r", encoding="utf-8") as f:
                        existing_logs = json.load(f)
                        if not isinstance(existing_logs, list):
                            existing_logs = [existing_logs]
                except Exception as e:
                    logger.warning(f"Failed to read existing log file, starting fresh: {e}")

            existing_logs.extend(logs)

            with open(file_abs_path, "w", encoding="utf-8") as f:
                json.dump(existing_logs, f, indent=2, ensure_ascii=False)

            if not repo.is_dirty() and not repo.untracked_files:
                logger.info("No new log changes detected. Repository is up-to-date.")
                return True

            repo.index.add([path])
            repo.index.commit(commit_message)

            logger.info("Pushing committed logs to remote...")
            repo.remotes.origin.push()
            logger.info("Successfully pushed logs to GitHub.")
            return True

        except git.exc.GitCommandError as e:
            err_msg = str(e).replace(self.token, "********")
            raise AdapterError(f"Git command failed: {err_msg}") from e
        except Exception as e:
            raise AdapterError(f"Failed to push logs to GitHub: {e}") from e
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
