"""SQLite database for Zotero library data."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS items (
    key TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    data TEXT NOT NULL,
    date_modified TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS collections (
    key TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    name TEXT NOT NULL,
    parent_key TEXT,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_state (
    library_id TEXT PRIMARY KEY,
    last_version INTEGER NOT NULL DEFAULT 0,
    last_synced_at TEXT NOT NULL
);
"""


class ZoteroDB:
    """SQLite storage for synced Zotero data."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # --- Items ---

    def upsert_item(self, item: dict) -> None:
        self.conn.execute(
            """INSERT INTO items (key, version, item_type, data, date_modified)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET
                 version=excluded.version,
                 item_type=excluded.item_type,
                 data=excluded.data,
                 date_modified=excluded.date_modified""",
            (
                item["key"],
                item["version"],
                item.get("data", {}).get("itemType", "unknown"),
                json.dumps(item),
                item.get("data", {}).get("dateModified", ""),
            ),
        )

    def upsert_items(self, items: list[dict]) -> None:
        for item in items:
            self.upsert_item(item)
        self.conn.commit()

    def delete_items(self, keys: list[str]) -> None:
        if not keys:
            return
        placeholders = ",".join("?" for _ in keys)
        self.conn.execute(f"DELETE FROM items WHERE key IN ({placeholders})", keys)
        self.conn.commit()

    def get_all_items(self) -> list[dict]:
        rows = self.conn.execute("SELECT data FROM items").fetchall()
        return [json.loads(row["data"]) for row in rows]

    def get_item_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) as cnt FROM items").fetchone()["cnt"]

    # --- Collections ---

    def upsert_collection(self, collection: dict) -> None:
        data = collection.get("data", {})
        self.conn.execute(
            """INSERT INTO collections (key, version, name, parent_key, data)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET
                 version=excluded.version,
                 name=excluded.name,
                 parent_key=excluded.parent_key,
                 data=excluded.data""",
            (
                collection["key"],
                collection["version"],
                data.get("name", ""),
                data.get("parentCollection", None),
                json.dumps(collection),
            ),
        )

    def upsert_collections(self, collections: list[dict]) -> None:
        for col in collections:
            self.upsert_collection(col)
        self.conn.commit()

    def delete_collections(self, keys: list[str]) -> None:
        if not keys:
            return
        placeholders = ",".join("?" for _ in keys)
        self.conn.execute(f"DELETE FROM collections WHERE key IN ({placeholders})", keys)
        self.conn.commit()

    def get_all_collections(self) -> list[dict]:
        rows = self.conn.execute("SELECT data FROM collections").fetchall()
        return [json.loads(row["data"]) for row in rows]

    def get_collection_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) as cnt FROM collections").fetchone()["cnt"]

    # --- Sync State ---

    def get_last_version(self, library_id: str) -> Optional[int]:
        row = self.conn.execute(
            "SELECT last_version FROM sync_state WHERE library_id = ?", (library_id,)
        ).fetchone()
        return row["last_version"] if row else None

    def set_last_version(self, library_id: str, version: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT INTO sync_state (library_id, last_version, last_synced_at)
               VALUES (?, ?, ?)
               ON CONFLICT(library_id) DO UPDATE SET
                 last_version=excluded.last_version,
                 last_synced_at=excluded.last_synced_at""",
            (library_id, version, now),
        )
        self.conn.commit()

    def get_sync_state(self, library_id: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM sync_state WHERE library_id = ?", (library_id,)
        ).fetchone()
        if row:
            return dict(row)
        return None
