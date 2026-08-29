import json
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError

from buildinpublic.config import get_config
from buildinpublic.git_monitor import CommitInfo
from buildinpublic.logger import logger


class SocialMediaPosts(BaseModel):
    title: str = Field(description="Short title or hook for the technical update")
    x_post: str = Field(description="Short, engaging X/Twitter post with relevant hashtags")
    linkedin_post: str = Field(description="Detailed, professional LinkedIn post with context and hashtags")


class ContentGenerator:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        config = get_config()
        self.api_key = api_key or config.gemini_api_key
        self.model_name = model_name or config.gemini_model
        self.client: Optional[genai.Client] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        if not self.api_key or self.api_key.startswith("your_gemini"):
            logger.warning("GEMINI_API_KEY is not set or using placeholder value.")
            self.client = None
            return

        try:
            self.client = genai.Client(api_key=self.api_key)
            logger.debug(f"Gemini client initialized with model {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self.client = None

    def construct_prompt(self, commit: CommitInfo) -> str:
        files_str = ", ".join(commit.changed_files[:10]) if commit.changed_files else "None"
        if len(commit.changed_files) > 10:
            files_str += f" (+{len(commit.changed_files) - 10} more)"

        prompt = f"""You are a technical content creator helping a software developer build in public.
Generate engaging social media progress updates based ONLY on the following Git commit details.

CRITICAL INSTRUCTION: Do NOT invent or fabricate any features, technologies, or changes that are not explicitly evidenced in the commit message or changed files list.

Git Commit Information:
- Commit SHA: {commit.short_sha}
- Author: {commit.author}
- Timestamp: {commit.timestamp.strftime('%Y-%m-%d %H:%M UTC')}
- Commit Message:
{commit.message}
- Diff Summary: {commit.diff_summary}
- Changed Files: {files_str}

Please generate two formatted social media posts:
1. X/Twitter Post:
   - Short, punchy, engaging.
   - Highlights the core technical change.
   - Includes 2-4 relevant tech hashtags.
   - Stay under 280 characters if possible.

2. LinkedIn Post:
   - Detailed and professional narrative.
   - Explains what was built/changed and why it matters.
   - Structured with clear formatting/bullet points.
   - Includes relevant technical concepts and hashtags.
"""
        return prompt

    def generate_posts(self, commit: CommitInfo) -> SocialMediaPosts:
        if not self.client:
            raise ValueError(
                "Gemini API client is not configured. Please set GEMINI_API_KEY in your .env file."
            )

        prompt = self.construct_prompt(commit)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SocialMediaPosts,
                    temperature=0.3,
                ),
            )

            if not response.text:
                raise ValueError("Received empty response from Gemini API.")

            # Parse JSON into Pydantic model
            data = json.loads(response.text)
            return SocialMediaPosts.model_validate(data)

        except APIError as api_err:
            logger.error(f"Gemini API returned an error: {api_err}")
            raise RuntimeError(f"Gemini API error: {api_err.message}") from api_err
        except json.JSONDecodeError as json_err:
            logger.error(f"Failed to parse LLM JSON response: {json_err}")
            raise ValueError("Gemini returned invalid JSON structure.") from json_err
        except Exception as e:
            logger.error(f"Unexpected error during content generation: {e}")
            raise
