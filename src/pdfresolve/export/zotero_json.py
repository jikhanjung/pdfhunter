"""Zotero JSON export functionality."""

import json
from pathlib import Path
from typing import Any

from pdfresolve.models.bibliography import BibliographyRecord


def record_to_zotero_json(record: BibliographyRecord) -> dict[str, Any]:
    """Convert a BibliographyRecord to Zotero JSON format.

    Args:
        record: BibliographyRecord to convert

    Returns:
        Zotero-compatible dictionary
    """
    return record.to_zotero_json()


def records_to_zotero_json(records: list[BibliographyRecord]) -> list[dict[str, Any]]:
    """Convert multiple records to Zotero JSON format.

    Args:
        records: List of BibliographyRecord objects

    Returns:
        List of Zotero-compatible dictionaries
    """
    return [record.to_zotero_json() for record in records]


def export_zotero_json(
    records: list[BibliographyRecord] | BibliographyRecord,
    output_path: str | Path,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> None:
    """Export records to a Zotero JSON file.

    Args:
        records: Single record or list of records
        output_path: Path to output file
        indent: JSON indentation (default 2)
        ensure_ascii: Whether to escape non-ASCII characters
    """
    if isinstance(records, BibliographyRecord):
        records = [records]

    zotero_data = records_to_zotero_json(records)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(zotero_data, f, indent=indent, ensure_ascii=ensure_ascii)


def export_zotero_json_string(
    records: list[BibliographyRecord] | BibliographyRecord,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> str:
    """Export records to a Zotero JSON string.

    Args:
        records: Single record or list of records
        indent: JSON indentation (default 2)
        ensure_ascii: Whether to escape non-ASCII characters

    Returns:
        Zotero JSON formatted string
    """
    if isinstance(records, BibliographyRecord):
        records = [records]

    zotero_data = records_to_zotero_json(records)
    return json.dumps(zotero_data, indent=indent, ensure_ascii=ensure_ascii)
