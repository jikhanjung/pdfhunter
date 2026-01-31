"""BibTeX export functionality."""

import re
from pathlib import Path
from typing import Any

from pdfresolve.models.bibliography import BibliographyRecord


# CSL type to BibTeX type mapping
CSL_TO_BIBTEX_TYPE = {
    "article": "article",
    "article-journal": "article",
    "article-magazine": "article",
    "article-newspaper": "article",
    "book": "book",
    "chapter": "incollection",
    "paper-conference": "inproceedings",
    "proceedings": "proceedings",
    "report": "techreport",
    "thesis": "phdthesis",
    "manuscript": "unpublished",
    "webpage": "misc",
    "dataset": "misc",
}

# Characters that need escaping in BibTeX
BIBTEX_SPECIAL_CHARS = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_bibtex(text: str) -> str:
    """Escape special characters for BibTeX.

    Args:
        text: Text to escape

    Returns:
        Escaped text
    """
    if not text:
        return ""

    for char, replacement in BIBTEX_SPECIAL_CHARS.items():
        text = text.replace(char, replacement)

    return text


def generate_cite_key(record: BibliographyRecord) -> str:
    """Generate a citation key for a record.

    Args:
        record: BibliographyRecord

    Returns:
        Citation key string
    """
    parts = []

    # First author's family name
    if record.author:
        first_author = record.author[0]
        if first_author.family:
            # Remove non-alphanumeric characters and take first 10 chars
            name = re.sub(r"[^a-zA-Z]", "", first_author.family)[:10]
            parts.append(name.lower())
        elif first_author.literal:
            name = re.sub(r"[^a-zA-Z]", "", first_author.literal.split()[0])[:10]
            parts.append(name.lower())

    # Year
    if record.issued and record.issued.year:
        parts.append(str(record.issued.year))

    # First word of title
    if record.title:
        first_word = re.sub(r"[^a-zA-Z]", "", record.title.split()[0])[:8]
        parts.append(first_word.lower())

    if parts:
        return "_".join(parts)

    # Fallback to record ID
    return re.sub(r"[^a-zA-Z0-9]", "_", record.id)


def format_authors_bibtex(record: BibliographyRecord) -> str:
    """Format authors for BibTeX.

    Args:
        record: BibliographyRecord

    Returns:
        BibTeX formatted author string
    """
    authors = []

    for author in record.author:
        if author.literal:
            authors.append(escape_bibtex(author.literal))
        elif author.family:
            name = escape_bibtex(author.family)
            if author.given:
                name += f", {escape_bibtex(author.given)}"
            authors.append(name)

    return " and ".join(authors)


def record_to_bibtex(
    record: BibliographyRecord,
    cite_key: str | None = None,
) -> str:
    """Convert a BibliographyRecord to BibTeX format.

    Args:
        record: BibliographyRecord to convert
        cite_key: Custom citation key (auto-generated if None)

    Returns:
        BibTeX formatted string
    """
    # Determine entry type
    bibtex_type = CSL_TO_BIBTEX_TYPE.get(record.type, "misc")

    # Generate or use provided cite key
    key = cite_key or generate_cite_key(record)

    lines = [f"@{bibtex_type}{{{key},"]

    # Authors
    if record.author:
        authors = format_authors_bibtex(record)
        lines.append(f"  author = {{{authors}}},")

    # Title
    if record.title:
        title = escape_bibtex(record.title)
        lines.append(f"  title = {{{{{title}}}}},")  # Double braces preserve case

    # Year
    if record.issued and record.issued.year:
        lines.append(f"  year = {{{record.issued.year}}},")
        if record.issued.month:
            lines.append(f"  month = {{{record.issued.month}}},")

    # Journal/Booktitle
    if record.container_title:
        container = escape_bibtex(record.container_title)
        if bibtex_type == "article":
            lines.append(f"  journal = {{{container}}},")
        elif bibtex_type in ["incollection", "inproceedings"]:
            lines.append(f"  booktitle = {{{container}}},")

    # Volume
    if record.volume:
        lines.append(f"  volume = {{{record.volume}}},")

    # Number/Issue
    if record.issue:
        lines.append(f"  number = {{{record.issue}}},")

    # Pages
    if record.page:
        # Normalize all dash types to BibTeX's double hyphen
        pages = record.page.replace("–", "--").replace("—", "--").replace("-", "--")
        # Clean up any triple+ hyphens
        while "---" in pages:
            pages = pages.replace("---", "--")
        lines.append(f"  pages = {{{pages}}},")

    # Publisher
    if record.publisher:
        publisher = escape_bibtex(record.publisher)
        lines.append(f"  publisher = {{{publisher}}},")

    # Address
    if record.publisher_place:
        address = escape_bibtex(record.publisher_place)
        lines.append(f"  address = {{{address}}},")

    # Series
    if record.collection_title:
        series = escape_bibtex(record.collection_title)
        lines.append(f"  series = {{{series}}},")

    # DOI
    if record.doi:
        lines.append(f"  doi = {{{record.doi}}},")

    # ISBN
    if record.isbn:
        lines.append(f"  isbn = {{{record.isbn}}},")

    # ISSN
    if record.issn:
        lines.append(f"  issn = {{{record.issn}}},")

    # Language
    if record.language:
        lines.append(f"  language = {{{record.language}}},")

    # Abstract
    if record.abstract:
        abstract = escape_bibtex(record.abstract)
        lines.append(f"  abstract = {{{abstract}}},")

    # Close entry
    lines.append("}")

    return "\n".join(lines)


def records_to_bibtex(
    records: list[BibliographyRecord],
    cite_keys: list[str] | None = None,
) -> str:
    """Convert multiple records to BibTeX format.

    Args:
        records: List of BibliographyRecord objects
        cite_keys: Optional list of citation keys (auto-generated if None)

    Returns:
        BibTeX formatted string with all records
    """
    if cite_keys is None:
        cite_keys = [None] * len(records)

    bibtex_entries = [
        record_to_bibtex(record, key)
        for record, key in zip(records, cite_keys)
    ]

    return "\n\n".join(bibtex_entries)


def export_bibtex(
    records: list[BibliographyRecord] | BibliographyRecord,
    output_path: str | Path,
    cite_keys: list[str] | None = None,
) -> None:
    """Export records to a BibTeX file.

    Args:
        records: Single record or list of records
        output_path: Path to output file
        cite_keys: Optional list of citation keys
    """
    if isinstance(records, BibliographyRecord):
        records = [records]
        if cite_keys:
            cite_keys = [cite_keys] if isinstance(cite_keys, str) else cite_keys

    bibtex_content = records_to_bibtex(records, cite_keys)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(bibtex_content)


def export_bibtex_string(
    records: list[BibliographyRecord] | BibliographyRecord,
    cite_keys: list[str] | None = None,
) -> str:
    """Export records to a BibTeX string.

    Args:
        records: Single record or list of records
        cite_keys: Optional list of citation keys

    Returns:
        BibTeX formatted string
    """
    if isinstance(records, BibliographyRecord):
        records = [records]
        if cite_keys:
            cite_keys = [cite_keys] if isinstance(cite_keys, str) else cite_keys

    return records_to_bibtex(records, cite_keys)
