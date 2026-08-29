from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import git
from git.exc import InvalidGitRepositoryError, NoSuchPathError

from buildinpublic.logger import logger


class CommitStats(BaseModel):
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0


class CommitInfo(BaseModel):
    sha: str
    short_sha: str
    author: str
    author_email: str
    timestamp: datetime
    message: str
    changed_files: List[str]
    stats: CommitStats
    diff_summary: Optional[str] = None


class GitMonitor:
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()
        self.repo: Optional[git.Repo] = None
        self._initialize_repo()

    def _initialize_repo(self) -> None:
        try:
            self.repo = git.Repo(self.repo_path, search_parent_directories=True)
            logger.debug(f"Git repository initialized at: {self.repo.working_tree_dir}")
        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            logger.error(f"Invalid Git repository path: {self.repo_path}")
            self.repo = None

    def is_valid_repo(self) -> bool:
        return self.repo is not None

    def get_recent_commits(self, max_count: int = 10) -> List[CommitInfo]:
        if not self.is_valid_repo():
            raise ValueError(f"Path '{self.repo_path}' is not a valid Git repository.")

        commits: List[CommitInfo] = []
        try:
            if not self.repo.heads:
                logger.info("Repository has no commits yet.")
                return []

            git_commits = list(self.repo.iter_commits(max_count=max_count))

            for c in git_commits:
                # Calculate stats and diff summary
                files_changed: List[str] = []
                insertions = 0
                deletions = 0

                if c.parents:
                    diff_stats = c.stats.total
                    files_changed = list(c.stats.files.keys())
                    insertions = diff_stats.get("insertions", 0)
                    deletions = diff_stats.get("deletions", 0)
                    num_files = diff_stats.get("files", len(files_changed))
                else:
                    # Initial commit handling
                    files_changed = list(c.stats.files.keys())
                    insertions = c.stats.total.get("insertions", 0)
                    deletions = c.stats.total.get("deletions", 0)
                    num_files = len(files_changed)

                stats = CommitStats(
                    files_changed=num_files,
                    insertions=insertions,
                    deletions=deletions,
                )

                commit_dt = datetime.fromtimestamp(c.committed_date, tz=timezone.utc)

                msg_str = c.message.decode("utf-8", errors="ignore") if isinstance(c.message, bytes) else str(c.message or "")
                commit_info = CommitInfo(
                    sha=c.hexsha,
                    short_sha=c.hexsha[:7],
                    author=c.author.name or "Unknown",
                    author_email=c.author.email or "",
                    timestamp=commit_dt,
                    message=msg_str.strip(),
                    changed_files=files_changed,
                    stats=stats,
                    diff_summary=f"+{insertions}/-{deletions} in {len(files_changed)} files",
                )

                commits.append(commit_info)
        except Exception as e:
            logger.error(f"Error reading commits from repository: {e}")
            raise

        return commits
