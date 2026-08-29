import time
import signal
import sys
from pathlib import Path
from typing import Optional

from buildinpublic.config import get_config
from buildinpublic.git_monitor import GitMonitor
from buildinpublic.storage import StorageManager
from buildinpublic.generator import ContentGenerator
from buildinpublic.publishers.console import ConsolePublisher
from buildinpublic.logger import logger


class BackgroundWatcher:
    def __init__(
        self,
        repo_path: Optional[Path] = None,
        poll_interval: Optional[int] = None,
        dry_run: bool = True,
    ):
        config = get_config()
        self.repo_path = repo_path or config.git_repo_path
        self.poll_interval = poll_interval or config.poll_interval_seconds
        self.dry_run = dry_run
        self.running = False

        self.git_mon = GitMonitor(self.repo_path)
        self.storage = StorageManager()
        self.publisher = ConsolePublisher()
        self.generator = ContentGenerator() if config.gemini_api_key and not config.gemini_api_key.startswith("your_gemini") else None

    def process_cycle(self) -> int:
        if not self.git_mon.is_valid_repo():
            logger.error(f"Invalid Git repository path: {self.repo_path}")
            return 0

        try:
            commits = self.git_mon.get_recent_commits(max_count=10)
        except Exception as e:
            logger.error(f"Error reading commits during poll cycle: {e}")
            return 0

        unprocessed = [c for c in commits if not self.storage.is_processed(c.sha)]
        if not unprocessed:
            logger.debug("No new unprocessed commits found.")
            return 0

        processed_count = 0
        for commit in reversed(unprocessed):  # Process older unprocessed commits first
            logger.info(f"New commit detected: {commit.short_sha} - {commit.message.split('\n')[0]}")
            
            if not self.generator:
                logger.error("Gemini API client not configured. Skipping post generation.")
                continue

            try:
                posts = self.generator.generate_posts(commit)
                success = self.publisher.publish(posts, dry_run=self.dry_run)
                
                if success:
                    # Mark as processed in storage only after successful post generation and publishing
                    self.storage.mark_processed(
                        sha=commit.sha,
                        generated_content=posts.model_dump(mode="json"),
                    )
                    processed_count += 1
            except Exception as err:
                logger.error(f"Failed to process commit {commit.short_sha}: {err}")
                # Commit remains unprocessed so it can be retried in future cycle

        return processed_count

    def run(self, max_cycles: Optional[int] = None) -> None:
        self.running = True
        logger.info(f"Starting Background Watcher (Poll interval: {self.poll_interval}s, Dry-run: {self.dry_run})")

        cycle_count = 0
        while self.running:
            try:
                count = self.process_cycle()
                if count > 0:
                    logger.info(f"Processed {count} commit(s) in this cycle.")
            except Exception as e:
                logger.error(f"Unexpected error in watcher cycle: {e}")

            cycle_count += 1
            if max_cycles and cycle_count >= max_cycles:
                logger.info(f"Reached maximum cycles ({max_cycles}). Exiting background watcher.")
                break

            # Sleep in 1-second increments to respond quickly to shutdown signals
            for _ in range(self.poll_interval):
                if not self.running:
                    break
                time.sleep(1)

        logger.info("Background Watcher stopped cleanly.")

    def stop(self) -> None:
        self.running = False
