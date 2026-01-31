"""Export Zotero DB contents to JSON files."""

import json
from pathlib import Path

from zoterosync.db import ZoteroDB


def export_to_json(db_path: Path, output_dir: Path) -> dict:
    """Export all items and collections from DB to JSON files.

    Creates:
      - output_dir/items.json
      - output_dir/collections.json

    Returns summary with counts.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    with ZoteroDB(db_path) as db:
        items = db.get_all_items()
        collections = db.get_all_collections()

    items_path = output_dir / "items.json"
    collections_path = output_dir / "collections.json"

    items_path.write_text(json.dumps(items, indent=2, ensure_ascii=False))
    collections_path.write_text(json.dumps(collections, indent=2, ensure_ascii=False))

    return {"items": len(items), "collections": len(collections)}
