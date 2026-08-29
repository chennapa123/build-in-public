from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

from buildinpublic.git_monitor import CommitInfo, CommitStats
from buildinpublic.generator import ContentGenerator, SocialMediaPosts


@pytest.fixture
def sample_commit():
    return CommitInfo(
        sha="1234567890abcdef1234567890abcdef12345678",
        short_sha="1234567",
        author="Dev User",
        author_email="dev@example.com",
        timestamp=datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc),
        message="feat: implement Gemini LLM content generation engine",
        changed_files=["buildinpublic/generator.py", "buildinpublic/cli.py"],
        stats=CommitStats(files_changed=2, insertions=45, deletions=5),
        diff_summary="+45/-5 in 2 files",
    )


def test_construct_prompt(sample_commit):
    generator = ContentGenerator(api_key="mock_key")
    prompt = generator.construct_prompt(sample_commit)

    assert "1234567" in prompt
    assert "Dev User" in prompt
    assert "feat: implement Gemini LLM content generation engine" in prompt
    assert "buildinpublic/generator.py" in prompt
    assert "CRITICAL INSTRUCTION" in prompt


def test_missing_api_key_raises_error(sample_commit):
    generator = ContentGenerator(api_key="")
    with pytest.raises(ValueError, match="Gemini API client is not configured"):
        generator.generate_posts(sample_commit)


@patch("buildinpublic.generator.genai.Client")
def test_successful_generation(mock_genai_client, sample_commit):
    mock_response = MagicMock()
    mock_response.text = '{"title": "Built Gemini LLM integration", "x_post": "Shipped LLM post generator! #buildinpublic #python", "linkedin_post": "Today I added Gemini API support for automated updates."}'
    
    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_response
    mock_genai_client.return_value = mock_client_instance

    generator = ContentGenerator(api_key="valid_key")
    posts = generator.generate_posts(sample_commit)

    assert isinstance(posts, SocialMediaPosts)
    assert posts.title == "Built Gemini LLM integration"
    assert "Shipped LLM" in posts.x_post
    assert "Gemini API" in posts.linkedin_post
