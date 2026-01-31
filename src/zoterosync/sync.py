"""Synchronization logic: full clone and incremental sync."""

import logging
from typing import Callable, Optional

from zoterosync.client import ZoteroClient
from zoterosync.config import ZoteroSyncConfig
from zoterosync.db import ZoteroDB

logger = logging.getLogger(__name__)

# Callback type: (stage_name, message)
LogCallback = Callable[[str, str], None]


def full_clone(
    config: ZoteroSyncConfig,
    on_log: Optional[LogCallback] = None,
) -> dict:
    """Download entire Zotero library into local SQLite database.

    Args:
        config: Zotero sync configuration.
        on_log: Optional callback for progress messages.

    Returns a summary dict with item/collection counts.
    """
    client = ZoteroClient(config)

    def _log(stage: str, msg: str):
        logger.info("[%s] %s", stage, msg)
        if on_log:
            on_log(stage, msg)

    _log("init", f"Connecting to Zotero library {config.zotero_library_id}")

    def _item_progress(fetched, total):
        if total:
            _log("items", f"Fetched {fetched}/{total} items")
        else:
            _log("items", f"Fetched {fetched} items")

    def _col_progress(fetched, total):
        if total:
            _log("collections", f"Fetched {fetched}/{total} collections")
        else:
            _log("collections", f"Fetched {fetched} collections")

    items = client.fetch_all_items(on_progress=_item_progress)
    collections = client.fetch_all_collections(on_progress=_col_progress)
    library_version = client.get_library_version()

    _log("db", f"Saving {len(items)} items and {len(collections)} collections to database")

    with ZoteroDB(config.db_path) as db:
        db.upsert_items(items)
        db.upsert_collections(collections)
        db.set_last_version(config.zotero_library_id, library_version)

    summary = {
        "items": len(items),
        "collections": len(collections),
        "library_version": library_version,
    }
    _log("done", f"Clone complete: {summary}")
    return summary


def incremental_sync(
    config: ZoteroSyncConfig,
    on_log: Optional[LogCallback] = None,
) -> dict:
    """Fetch only changes since last sync.

    Args:
        config: Zotero sync configuration.
        on_log: Optional callback for progress messages.

    Returns a summary dict with counts of updated/deleted items.
    """
    client = ZoteroClient(config)

    def _log(stage: str, msg: str):
        logger.info("[%s] %s", stage, msg)
        if on_log:
            on_log(stage, msg)

    with ZoteroDB(config.db_path) as db:
        last_version = db.get_last_version(config.zotero_library_id)

        if last_version is None:
            _log("init", "No previous sync found, performing full clone")
            db.close()
            return full_clone(config, on_log=on_log)

        _log("init", f"Syncing changes since version {last_version}")

        def _item_progress(fetched, total):
            if total:
                _log("items", f"Fetched {fetched}/{total} changed items")
            else:
                _log("items", f"Fetched {fetched} changed items")

        def _col_progress(fetched, total):
            if total:
                _log("collections", f"Fetched {fetched}/{total} changed collections")
            else:
                _log("collections", f"Fetched {fetched} changed collections")

        new_items = client.fetch_items_since(last_version, on_progress=_item_progress)
        new_collections = client.fetch_collections_since(
            last_version, on_progress=_col_progress
        )
        deleted = client.fetch_deleted_since(last_version)
        library_version = client.get_library_version()

        deleted_items = deleted.get("items", [])
        deleted_collections = deleted.get("collections", [])

        _log(
            "db",
            f"Applying {len(new_items)} item updates, "
            f"{len(deleted_items)} item deletions",
        )

        db.upsert_items(new_items)
        db.upsert_collections(new_collections)
        db.delete_items(deleted_items)
        db.delete_collections(deleted_collections)
        db.set_last_version(config.zotero_library_id, library_version)

    summary = {
        "updated_items": len(new_items),
        "updated_collections": len(new_collections),
        "deleted_items": len(deleted_items),
        "deleted_collections": len(deleted_collections),
        "library_version": library_version,
    }
    _log("done", f"Sync complete: {summary}")
    return summary
