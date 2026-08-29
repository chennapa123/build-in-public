import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from buildinpublic.logger import logger


class ProcessedCommitRecord(BaseModel):
    sha: str
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    generated_content: Optional[Dict[str, Any]] = None


class StorageManager:
    def __init__(self, history_file: Optional[Path] = None):
        self.history_file = history_file or Path(".buildinpublic_history.json").resolve()
        self._ensure_history_file()

    def _ensure_history_file(self) -> None:
        if not self.history_file.exists():
            try:
                self.history_file.write_text(json.dumps({"processed_commits": {}}, indent=2), encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to create history file at {self.history_file}: {e}")

    def _load_data(self) -> Dict[str, Any]:
        if not self.history_file.exists():
            return {"processed_commits": {}}
        try:
            content = self.history_file.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception as e:
            logger.error(f"Error loading history file {self.history_file}: {e}")
            return {"processed_commits": {}}

    def _save_data(self, data: Dict[str, Any]) -> None:
        try:
            self.history_file.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        except Exception as e:
            logger.error(f"Error saving history file {self.history_file}: {e}")

    def is_processed(self, sha: str) -> bool:
        data = self._load_data()
        processed_commits = data.get("processed_commits", {})
        return sha in processed_commits

    def mark_processed(self, sha: str, generated_content: Optional[Dict[str, Any]] = None) -> ProcessedCommitRecord:
        data = self._load_data()
        record = ProcessedCommitRecord(
            sha=sha,
            processed_at=datetime.now(timezone.utc),
            generated_content=generated_content,
        )
        if "processed_commits" not in data:
            data["processed_commits"] = {}
        
        data["processed_commits"][sha] = record.model_dump(mode="json")
        self._save_data(data)
        logger.info(f"Marked commit {sha[:7]} as processed.")
        return record

    def get_processed_commits(self) -> List[ProcessedCommitRecord]:
        data = self._load_data()
        records_dict = data.get("processed_commits", {})
        records: List[ProcessedCommitRecord] = []
        for sha, item in records_dict.items():
            try:
                records.append(ProcessedCommitRecord.model_validate(item))
            except Exception as e:
                logger.warning(f"Error parsing history record for SHA {sha}: {e}")
        
        # Sort by processed_at descending
        records.sort(key=lambda x: x.processed_at, reverse=True)
        return records
