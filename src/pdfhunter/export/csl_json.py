"""CSL-JSON export functionality."""

import json
from pathlib import Path
from typing import Any

from pdfhunter.models.bibliography import BibliographyRecord


def record_to_csl_json(record: BibliographyRecord) -> dict[str, Any]:
    """Convert a BibliographyRecord to CSL-JSON format.

    Args:
        record: BibliographyRecord to convert

    Returns:
        CSL-JSON compatible dictionary
    """
    return record.to_csl_json()


def records_to_csl_json(records: list[BibliographyRecord]) -> list[dict[str, Any]]:
    """Convert multiple records to CSL-JSON format.

    Args:
        records: List of BibliographyRecord objects

    Returns:
        List of CSL-JSON compatible dictionaries
    """
    return [record.to_csl_json() for record in records]


def export_csl_json(
    records: list[BibliographyRecord] | BibliographyRecord,
    output_path: str | Path,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> None:
    """Export records to a CSL-JSON file.

    Args:
        records: Single record or list of records
        output_path: Path to output file
        indent: JSON indentation (default 2)
        ensure_ascii: Whether to escape non-ASCII characters
    """
    if isinstance(records, BibliographyRecord):
        records = [records]

    csl_data = records_to_csl_json(records)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(csl_data, f, indent=indent, ensure_ascii=ensure_ascii)


def export_csl_json_string(
    records: list[BibliographyRecord] | BibliographyRecord,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> str:
    """Export records to a CSL-JSON string.

    Args:
        records: Single record or list of records
        indent: JSON indentation (default 2)
        ensure_ascii: Whether to escape non-ASCII characters

    Returns:
        CSL-JSON formatted string
    """
    if isinstance(records, BibliographyRecord):
        records = [records]

    csl_data = records_to_csl_json(records)
    return json.dumps(csl_data, indent=indent, ensure_ascii=ensure_ascii)


def load_csl_json(input_path: str | Path) -> list[dict[str, Any]]:
    """Load CSL-JSON data from a file.

    Args:
        input_path: Path to CSL-JSON file

    Returns:
        List of CSL-JSON dictionaries
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        return [data]
    return data
