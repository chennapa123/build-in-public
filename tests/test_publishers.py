from buildinpublic.generator import SocialMediaPosts
from buildinpublic.publishers.console import ConsolePublisher
from buildinpublic.publishers.x_twitter import XTwitterPublisher


def test_console_publisher():
    publisher = ConsolePublisher()
    assert publisher.name() == "Console / Terminal Output"

    posts = SocialMediaPosts(
        title="Test Post Title",
        x_post="Test X Post #python",
        linkedin_post="Test LinkedIn Post",
    )

    result = publisher.publish(posts, dry_run=True)
    assert result is True


def test_x_publisher_missing_credentials(monkeypatch):
    monkeypatch.delenv("X_API_KEY", raising=False)
    monkeypatch.delenv("X_API_SECRET", raising=False)
    monkeypatch.delenv("X_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("X_ACCESS_TOKEN_SECRET", raising=False)

    publisher = XTwitterPublisher()
    assert publisher.name() == "X / Twitter API"
    assert not publisher.has_credentials()

    posts = SocialMediaPosts(
        title="Test Title",
        x_post="Test X Post",
        linkedin_post="Test LinkedIn Post",
    )

    # Dry run should succeed even without credentials
    assert publisher.publish(posts, dry_run=True) is True

    # Live run without credentials should fail gracefully
    assert publisher.publish(posts, dry_run=False) is False
