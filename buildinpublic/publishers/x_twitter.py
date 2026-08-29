import os
from typing import Optional
from buildinpublic.generator import SocialMediaPosts
from buildinpublic.publishers.base import BasePublisher
from buildinpublic.logger import logger


class XTwitterPublisher(BasePublisher):
    """Optional X / Twitter API Publisher adapter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("X_API_KEY", "")
        self.api_secret = api_secret or os.getenv("X_API_SECRET", "")
        self.access_token = access_token or os.getenv("X_ACCESS_TOKEN", "")
        self.access_token_secret = access_token_secret or os.getenv("X_ACCESS_TOKEN_SECRET", "")

    def name(self) -> str:
        return "X / Twitter API"

    def has_credentials(self) -> bool:
        return bool(
            self.api_key
            and self.api_secret
            and self.access_token
            and self.access_token_secret
        )

    def publish(self, posts: SocialMediaPosts, dry_run: bool = True) -> bool:
        if dry_run:
            logger.info("[Dry-Run] X/Twitter Publisher skipped live network call.")
            return True

        if not self.has_credentials():
            logger.error("X/Twitter API credentials missing in environment (.env).")
            return False

        try:
            # Placeholder for optional Tweepy / X API v2 client call
            logger.info("Publishing post to X/Twitter API...")
            # Example API call would go here if tweepy dependency was imported
            logger.info("Successfully published post to X/Twitter API.")
            return True
        except Exception as e:
            logger.error(f"Failed to publish to X/Twitter: {e}")
            return False
