"""Tests for the zoterosync module."""

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zoterosync.config import ZoteroSyncConfig
from zoterosync.db import ZoteroDB
from zoterosync.export import export_to_json


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary database."""
    db_path = tmp_path / "test.db"
    with ZoteroDB(db_path) as db:
        yield db, db_path


@pytest.fixture
def sample_item():
    return {
        "key": "ABC123",
        "version": 42,
        "data": {
            "itemType": "journalArticle",
            "title": "Test Article",
            "dateModified": "2024-01-15T10:00:00Z",
        },
    }


@pytest.fixture
def sample_collection():
    return {
        "key": "COL001",
        "version": 10,
        "data": {
            "name": "My Collection",
            "parentCollection": None,
        },
    }


class TestZoteroDB:
    def test_upsert_and_get_items(self, tmp_db, sample_item):
        db, _ = tmp_db
        db.upsert_items([sample_item])
        items = db.get_all_items()
        assert len(items) == 1
        assert items[0]["key"] == "ABC123"

    def test_upsert_updates_existing(self, tmp_db, sample_item):
        db, _ = tmp_db
        db.upsert_items([sample_item])

        sample_item["version"] = 43
        sample_item["data"]["title"] = "Updated Title"
        db.upsert_items([sample_item])

        items = db.get_all_items()
        assert len(items) == 1
        assert items[0]["version"] == 43

    def test_delete_items(self, tmp_db, sample_item):
        db, _ = tmp_db
        db.upsert_items([sample_item])
        db.delete_items(["ABC123"])
        assert db.get_item_count() == 0

    def test_delete_empty_list(self, tmp_db):
        db, _ = tmp_db
        db.delete_items([])  # should not raise

    def test_collections_crud(self, tmp_db, sample_collection):
        db, _ = tmp_db
        db.upsert_collections([sample_collection])
        cols = db.get_all_collections()
        assert len(cols) == 1
        assert cols[0]["key"] == "COL001"

        db.delete_collections(["COL001"])
        assert db.get_collection_count() == 0

    def test_sync_state(self, tmp_db):
        db, _ = tmp_db
        assert db.get_last_version("lib1") is None

        db.set_last_version("lib1", 100)
        assert db.get_last_version("lib1") == 100

        state = db.get_sync_state("lib1")
        assert state["last_version"] == 100
        assert state["last_synced_at"] is not None

        # Update
        db.set_last_version("lib1", 200)
        assert db.get_last_version("lib1") == 200


class TestExport:
    def test_export_to_json(self, tmp_path, sample_item, sample_collection):
        db_path = tmp_path / "export_test.db"
        output_dir = tmp_path / "output"

        with ZoteroDB(db_path) as db:
            db.upsert_items([sample_item])
            db.upsert_collections([sample_collection])

        result = export_to_json(db_path, output_dir)
        assert result == {"items": 1, "collections": 1}

        items = json.loads((output_dir / "items.json").read_text())
        assert len(items) == 1
        assert items[0]["key"] == "ABC123"


class TestConfig:
    def test_default_config(self):
        config = ZoteroSyncConfig(
            zotero_api_key="test_key",
            zotero_library_id="12345",
        )
        assert config.zotero_library_type == "user"
        assert config.db_path == Path("data/zotero/zotero.db")


class TestSync:
    @patch("zoterosync.sync.ZoteroClient")
    def test_full_clone(self, mock_client_cls, tmp_path):
        from zoterosync.sync import full_clone

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.fetch_all_items.return_value = [
            {"key": "A1", "version": 1, "data": {"itemType": "book", "dateModified": ""}}
        ]
        mock_client.fetch_all_collections.return_value = []
        mock_client.get_library_version.return_value = 50

        config = ZoteroSyncConfig(
            zotero_api_key="key",
            zotero_library_id="lib1",
            zotero_data_dir=tmp_path,
        )
        result = full_clone(config)
        assert result["items"] == 1
        assert result["collections"] == 0
        assert result["library_version"] == 50

        # Verify DB state
        with ZoteroDB(config.db_path) as db:
            assert db.get_item_count() == 1
            assert db.get_last_version("lib1") == 50

    @patch("zoterosync.sync.ZoteroClient")
    def test_incremental_sync(self, mock_client_cls, tmp_path):
        from zoterosync.sync import incremental_sync

        config = ZoteroSyncConfig(
            zotero_api_key="key",
            zotero_library_id="lib1",
            zotero_data_dir=tmp_path,
        )

        # Set up initial state
        with ZoteroDB(config.db_path) as db:
            db.upsert_items([
                {"key": "A1", "version": 1, "data": {"itemType": "book", "dateModified": ""}}
            ])
            db.set_last_version("lib1", 50)

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.fetch_items_since.return_value = [
            {"key": "A2", "version": 2, "data": {"itemType": "article", "dateModified": ""}}
        ]
        mock_client.fetch_collections_since.return_value = []
        mock_client.fetch_deleted_since.return_value = {"items": [], "collections": []}
        mock_client.get_library_version.return_value = 55

        result = incremental_sync(config)
        assert result["updated_items"] == 1
        assert result["library_version"] == 55

        with ZoteroDB(config.db_path) as db:
            assert db.get_item_count() == 2
            assert db.get_last_version("lib1") == 55
