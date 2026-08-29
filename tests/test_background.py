from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from buildinpublic.git_monitor import CommitInfo, CommitStats
from buildinpublic.generator import SocialMediaPosts
from buildinpublic.watcher import BackgroundWatcher


@pytest.fixture
def mock_commit():
    return CommitInfo(
        sha="9999888877776666555544443333222211110000",
        short_sha="9999888",
        author="Background User",
        author_email="watcher@example.com",
        timestamp=datetime.now(timezone.utc),
        message="feat: background watcher test commit",
        changed_files=["app.py"],
        stats=CommitStats(files_changed=1, insertions=10, deletions=2),
    )


def test_background_watcher_single_cycle(tmp_path: Path, mock_commit):
    history_file = tmp_path / "watcher_history.json"
    
    with patch("buildinpublic.watcher.GitMonitor") as mock_git_cls, \
         patch("buildinpublic.watcher.ContentGenerator") as mock_gen_cls:
        
        mock_git = MagicMock()
        mock_git.is_valid_repo.return_value = True
        mock_git.get_recent_commits.return_value = [mock_commit]
        mock_git_cls.return_value = mock_git

        mock_gen = MagicMock()
        mock_gen.generate_posts.return_value = SocialMediaPosts(
            title="Watcher Test",
            x_post="Test post #buildinpublic",
            linkedin_post="Test LinkedIn post",
        )
        mock_gen_cls.return_value = mock_gen

        watcher = BackgroundWatcher(repo_path=tmp_path, poll_interval=1, dry_run=True)
        watcher.storage.history_file = history_file
        watcher.generator = mock_gen

        processed_count = watcher.process_cycle()

        assert processed_count == 1
        assert watcher.storage.is_processed(mock_commit.sha)

        # Second cycle should detect it as already processed
        second_count = watcher.process_cycle()
        assert second_count == 0


def test_background_watcher_error_retry(tmp_path: Path, mock_commit):
    history_file = tmp_path / "watcher_history.json"

    with patch("buildinpublic.watcher.GitMonitor") as mock_git_cls:
        mock_git = MagicMock()
        mock_git.is_valid_repo.return_value = True
        mock_git.get_recent_commits.return_value = [mock_commit]
        mock_git_cls.return_value = mock_git

        watcher = BackgroundWatcher(repo_path=tmp_path, poll_interval=1, dry_run=True)
        watcher.storage.history_file = history_file
        
        # Generator fails
        mock_gen = MagicMock()
        mock_gen.generate_posts.side_effect = RuntimeError("LLM Timeout")
        watcher.generator = mock_gen

        processed_count = watcher.process_cycle()

        assert processed_count == 0
        # Commit must NOT be marked processed if generator failed
        assert not watcher.storage.is_processed(mock_commit.sha)
