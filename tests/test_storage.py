import json
from pathlib import Path
import pytest
from buildinpublic.storage import StorageManager


def test_empty_history(tmp_path: Path):
    history_file = tmp_path / "history_test.json"
    storage = StorageManager(history_file=history_file)

    assert history_file.exists()
    assert storage.get_processed_commits() == []
    assert not storage.is_processed("abcd1234efgh")


def test_mark_processed_and_check(tmp_path: Path):
    history_file = tmp_path / "history_test.json"
    storage = StorageManager(history_file=history_file)

    sha = "1234567890abcdef"
    content = {"x_post": "Hello Twitter", "linkedin_post": "Hello LinkedIn"}

    assert not storage.is_processed(sha)

    record = storage.mark_processed(sha=sha, generated_content=content)

    assert storage.is_processed(sha)
    assert record.sha == sha
    assert record.generated_content == content

    records = storage.get_processed_commits()
    assert len(records) == 1
    assert records[0].sha == sha
    assert records[0].generated_content == content


def test_prevent_duplicates(tmp_path: Path):
    history_file = tmp_path / "history_test.json"
    storage = StorageManager(history_file=history_file)

    sha = "1234567890abcdef"
    storage.mark_processed(sha=sha, generated_content={"v": 1})
    storage.mark_processed(sha=sha, generated_content={"v": 2})

    records = storage.get_processed_commits()
    # Unique SHA entry should overwrite/update rather than duplicate in records map
    assert len(records) == 1
    assert records[0].generated_content == {"v": 2}


def test_persistence(tmp_path: Path):
    history_file = tmp_path / "history_test.json"
    
    # Instance 1 writes
    storage1 = StorageManager(history_file=history_file)
    storage1.mark_processed("sha1")

    # Instance 2 reads
    storage2 = StorageManager(history_file=history_file)
    assert storage2.is_processed("sha1")
    assert not storage2.is_processed("sha2")
