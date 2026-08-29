import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file if it exists
load_dotenv()

class Config(BaseModel):
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    git_repo_path: Path = Field(default_factory=lambda: Path(os.getenv("GIT_REPO_PATH", ".")).resolve())
    poll_interval_seconds: int = Field(default_factory=lambda: int(os.getenv("POLL_INTERVAL_SECONDS", "300")))
    dry_run: bool = Field(default_factory=lambda: os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes"))

    def validate_git_path(self) -> bool:
        return self.git_repo_path.exists() and self.git_repo_path.is_dir()

def get_config() -> Config:
    return Config()
