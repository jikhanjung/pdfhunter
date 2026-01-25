"""RIS (Research Information Systems) export functionality."""

from pathlib import Path
from typing import Any

from pdfhunter.models.bibliography import BibliographyRecord


# CSL type to RIS type mapping
CSL_TO_RIS_TYPE = {
    "article": "JOUR",
    "article-journal": "JOUR",
    "article-magazine": "MGZN",
    "article-newspaper": "NEWS",
    "book": "BOOK",
    "chapter": "CHAP",
    "paper-conference": "CPAPER",
    "proceedings": "CONF",
    "report": "RPRT",
    "thesis": "THES",
    "manuscript": "MANSCPT",
    "map": "MAP",
    "patent": "PAT",
    "personal_communication": "PCOMM",
    "webpage": "ELEC",
    "dataset": "DATA",
}


def record_to_ris(record: BibliographyRecord) -> str:
    """Convert a BibliographyRecord to RIS format.

    Args:
        record: BibliographyRecord to convert

    Returns:
        RIS formatted string
    """
    lines = []

    # Type
    ris_type = CSL_TO_RIS_TYPE.get(record.type, "GEN")
    lines.append(f"TY  - {ris_type}")

    # ID
    lines.append(f"ID  - {record.id}")

    # Title
    if record.title:
        lines.append(f"TI  - {record.title}")
        lines.append(f"T1  - {record.title}")

    # Authors
    for author in record.author:
        if author.literal:
            lines.append(f"AU  - {author.literal}")
        elif author.family:
            name = author.family
            if author.given:
                name += f", {author.given}"
            lines.append(f"AU  - {name}")

    # Year/Date
    if record.issued and record.issued.year:
        year = record.issued.year
        lines.append(f"PY  - {year}")
        if record.issued.month:
            month = str(record.issued.month).zfill(2)
            day = str(record.issued.day).zfill(2) if record.issued.day else "01"
            lines.append(f"DA  - {year}/{month}/{day}")

    # Journal/Container
    if record.container_title:
        if record.type in ["article", "article-journal"]:
            lines.append(f"JO  - {record.container_title}")
            lines.append(f"JF  - {record.container_title}")
        else:
            lines.append(f"T2  - {record.container_title}")

    # Volume
    if record.volume:
        lines.append(f"VL  - {record.volume}")

    # Issue
    if record.issue:
        lines.append(f"IS  - {record.issue}")

    # Pages
    if record.page:
        pages = record.page.replace("–", "-").replace("—", "-")
        if "-" in pages:
            start, end = pages.split("-", 1)
            lines.append(f"SP  - {start.strip()}")
            lines.append(f"EP  - {end.strip()}")
        else:
            lines.append(f"SP  - {pages}")

    # Publisher
    if record.publisher:
        lines.append(f"PB  - {record.publisher}")

    # Place
    if record.publisher_place:
        lines.append(f"CY  - {record.publisher_place}")

    # Series
    if record.collection_title:
        lines.append(f"T3  - {record.collection_title}")

    # DOI
    if record.doi:
        lines.append(f"DO  - {record.doi}")

    # ISSN
    if record.issn:
        lines.append(f"SN  - {record.issn}")

    # ISBN
    if record.isbn:
        lines.append(f"SN  - {record.isbn}")

    # Language
    if record.language:
        lines.append(f"LA  - {record.language}")

    # Abstract
    if record.abstract:
        lines.append(f"AB  - {record.abstract}")

    # End of record
    lines.append("ER  - ")

    return "\n".join(lines)


def records_to_ris(records: list[BibliographyRecord]) -> str:
    """Convert multiple records to RIS format.

    Args:
        records: List of BibliographyRecord objects

    Returns:
        RIS formatted string with all records
    """
    ris_entries = [record_to_ris(record) for record in records]
    return "\n\n".join(ris_entries)


def export_ris(
    records: list[BibliographyRecord] | BibliographyRecord,
    output_path: str | Path,
) -> None:
    """Export records to a RIS file.

    Args:
        records: Single record or list of records
        output_path: Path to output file
    """
    if isinstance(records, BibliographyRecord):
        records = [records]

    ris_content = records_to_ris(records)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ris_content)


def export_ris_string(
    records: list[BibliographyRecord] | BibliographyRecord,
) -> str:
    """Export records to a RIS string.

    Args:
        records: Single record or list of records

    Returns:
        RIS formatted string
    """
    if isinstance(records, BibliographyRecord):
        records = [records]

    return records_to_ris(records)
