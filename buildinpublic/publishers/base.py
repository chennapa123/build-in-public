from abc import ABC, abstractmethod
from typing import Any, Dict
from buildinpublic.generator import SocialMediaPosts


class BasePublisher(ABC):
    """Abstract interface for all social media publisher adapters."""

    @abstractmethod
    def name(self) -> str:
        """Return the friendly name of the publisher."""
        pass

    @abstractmethod
    def publish(self, posts: SocialMediaPosts, dry_run: bool = True) -> bool:
        """
        Publish generated social media posts.

        Args:
            posts: SocialMediaPosts object containing title, x_post, linkedin_post.
            dry_run: If True, do not perform live API calls; output to dry-run handler.

        Returns:
            bool: True if publishing/handling succeeded, False otherwise.
        """
        pass
