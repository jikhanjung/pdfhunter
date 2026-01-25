"""Regex patterns for bibliographic field extraction."""

import re
from dataclasses import dataclass
from typing import Any

from ..models.evidence import BoundingBox


@dataclass
class PatternMatch:
    """A matched pattern with metadata."""

    field_name: str
    value: str
    raw_match: str
    start: int
    end: int
    confidence: float = 1.0
    pattern_name: str | None = None
    page_number: int | None = None
    bbox: BoundingBox | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d = {
            "field_name": self.field_name,
            "value": self.value,
            "raw_match": self.raw_match,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "pattern_name": self.pattern_name,
            "page_number": self.page_number,
        }
        if self.bbox:
            d["bbox"] = self.bbox.to_list()
        return d


# Year patterns
YEAR_PATTERNS = [
    # Standard 4-digit years
    (r"\b(19[0-9]{2}|20[0-2][0-9])\b", "year_standard"),
    # Year in parentheses
    (r"\((\d{4})\)", "year_parentheses"),
    # Year with copyright
    (r"[©℗]\s*(19[0-9]{2}|20[0-2][0-9])", "year_copyright"),
    # Year range (take first year)
    (r"\b(19[0-9]{2}|20[0-2][0-9])[-–—](19[0-9]{2}|20[0-2][0-9])\b", "year_range"),
]

# Page patterns
PAGE_PATTERNS = [
    # p. 123-456 or pp. 123-456
    (r"\bp{1,2}\.\s*(\d+)\s*[-–—]\s*(\d+)\b", "pages_p_range"),
    # pages 123-456
    (r"\bpages?\s+(\d+)\s*[-–—]\s*(\d+)\b", "pages_word_range"),
    # S. 123-456 (German)
    (r"\bS\.\s*(\d+)\s*[-–—]\s*(\d+)\b", "pages_german"),
    # с. 123-456 (Russian)
    (r"\bс\.\s*(\d+)\s*[-–—]\s*(\d+)\b", "pages_russian"),
    # :123-456 (after volume)
    (r":\s*(\d+)\s*[-–—]\s*(\d+)\b", "pages_colon"),
    # Single page: p. 123
    (r"\bp\.\s*(\d+)\b(?!\s*[-–—])", "page_single"),
]

# Volume patterns
VOLUME_PATTERNS = [
    # Vol. X or Volume X
    (r"\b[Vv]ol(?:ume)?\.?\s*([IVXLCDM]+|\d+)\b", "volume_standard"),
    # v. X
    (r"\bv\.\s*(\d+)\b", "volume_abbrev"),
    # t. X or tome X (French)
    (r"\b[Tt](?:ome)?\.?\s*([IVXLCDM]+|\d+)\b", "volume_french"),
    # Том X (Russian)
    (r"\b[Тт]ом\.?\s*(\d+|[IVXLCDM]+)\b", "volume_russian"),
    # Bd. X (German)
    (r"\bBd\.?\s*(\d+)\b", "volume_german"),
    # Roman numerals standalone in specific context
    (r"\(([IVXLCDM]+)\)", "volume_roman_paren"),
    # Roman numeral after comma (common in journal citations)
    (r",\s*([IVXLCDM]+)\s*,", "volume_roman_comma"),
]

# Issue patterns
ISSUE_PATTERNS = [
    # No. X or Number X
    (r"\b[Nn]o\.?\s*(\d+)\b", "issue_standard"),
    # n° X or № X
    (r"[n№]°?\s*(\d+)\b", "issue_numero"),
    # Issue X
    (r"\b[Ii]ssue\s+(\d+)\b", "issue_word"),
    # Heft X (German)
    (r"\bHeft\.?\s*(\d+)\b", "issue_german"),
    # Выпуск X (Russian)
    (r"\b[Вв]ыпуск\.?\s*(\d+)\b", "issue_russian"),
    # fasc. X (fascicle)
    (r"\b[Ff]asc(?:icule)?\.?\s*(\d+)\b", "issue_fascicle"),
    # (1) or (2) after volume
    (r"\b\d+\s*\((\d+)\)", "issue_in_paren"),
]

# Series patterns
SERIES_PATTERNS = [
    # Bulletin No. X
    (r"\bBulletin\s+[Nn]o\.?\s*(\d+)\b", "series_bulletin"),
    # Memoir X or Memoirs X
    (r"\bMemoirs?\s+(\d+)\b", "series_memoir"),
    # Труды X (Russian proceedings)
    (r"\b[Тт]руды\b.*?(\d+)", "series_trudy"),
    # Известия (Russian news/bulletin)
    (r"\b[Ии]звестия\b", "series_izvestiya"),
    # Записки (Russian notes)
    (r"\b[Зз]аписки\b", "series_zapiski"),
    # Ser. X or Series X
    (r"\b[Ss]er(?:ies)?\.?\s*([A-Z]|\d+)\b", "series_standard"),
    # n.s. (new series)
    (r"\bn\.?\s*s\.?\b", "series_new"),
]

# Publisher place patterns (common cities)
PLACE_PATTERNS = [
    # Major publishing cities
    (r"\b(Paris|London|New York|Berlin|Vienna|Wien|Moscow|Москва)\b", "place_major"),
    (r"\b(Leipzig|Munich|München|Oxford|Cambridge|Chicago|Tokyo)\b", "place_major2"),
    (r"\b(Amsterdam|Rotterdam|Leiden|The Hague|Den Haag)\b", "place_dutch"),
    (r"\b(Madrid|Barcelona|Rome|Roma|Milan|Milano|Firenze|Florence)\b", "place_southern"),
    (r"\b(Ленинград\w*|Leningrad|Санкт-Петербург\w*|St\.?\s*Petersburg)\b", "place_russia"),
    (r"\b(Киев|Kiev|Kyiv|Минск|Minsk)\b", "place_eastern"),
    (r"\b(Stockholm|Copenhagen|København|Oslo|Helsinki)\b", "place_nordic"),
    (r"\b(Washington|Philadelphia|Boston|Norman|Lawrence)\b", "place_us"),
    (r"\b(Toronto|Montreal|Montréal|Vancouver|Ottawa)\b", "place_canada"),
    (r"\b(Sydney|Melbourne|Canberra|Brisbane)\b", "place_australia"),
    # Pattern: City followed by colon (often publisher location)
    (r"([A-Z][a-zа-яé]+(?:\s+[A-Z][a-zа-яé]+)?)\s*:", "place_before_colon"),
]

# DOI patterns
DOI_PATTERNS = [
    (r"\b(10\.\d{4,}/[^\s]+)\b", "doi_standard"),
    (r"doi\.org/(10\.\d{4,}/[^\s]+)", "doi_url"),
    (r"[Dd][Oo][Ii]:\s*(10\.\d{4,}/[^\s]+)", "doi_prefix"),
]

# ISSN/ISBN patterns
IDENTIFIER_PATTERNS = [
    # ISSN
    (r"\bISSN[:\s]*(\d{4}[-–]\d{3}[\dXx])\b", "issn"),
    # ISBN-13
    (r"\bISBN[:\s]*(97[89][-–\s]?\d{1,5}[-–\s]?\d{1,7}[-–\s]?\d{1,7}[-–\s]?\d)\b", "isbn13"),
    # ISBN-10
    (r"\bISBN[:\s]*(\d{1,5}[-–\s]?\d{1,7}[-–\s]?\d{1,7}[-–\s]?[\dXx])\b", "isbn10"),
]


def compile_patterns(
    pattern_list: list[tuple[str, str]],
) -> list[tuple[re.Pattern, str]]:
    """Compile a list of pattern tuples.

    Args:
        pattern_list: List of (pattern_string, pattern_name) tuples

    Returns:
        List of (compiled_pattern, pattern_name) tuples
    """
    return [(re.compile(p, re.IGNORECASE | re.UNICODE), name) for p, name in pattern_list]


# Pre-compiled patterns
COMPILED_YEAR_PATTERNS = compile_patterns(YEAR_PATTERNS)
COMPILED_PAGE_PATTERNS = compile_patterns(PAGE_PATTERNS)
COMPILED_VOLUME_PATTERNS = compile_patterns(VOLUME_PATTERNS)
COMPILED_ISSUE_PATTERNS = compile_patterns(ISSUE_PATTERNS)
COMPILED_SERIES_PATTERNS = compile_patterns(SERIES_PATTERNS)
COMPILED_PLACE_PATTERNS = compile_patterns(PLACE_PATTERNS)
COMPILED_DOI_PATTERNS = compile_patterns(DOI_PATTERNS)
COMPILED_IDENTIFIER_PATTERNS = compile_patterns(IDENTIFIER_PATTERNS)


def roman_to_int(roman: str) -> int:
    """Convert Roman numeral to integer.

    Args:
        roman: Roman numeral string

    Returns:
        Integer value
    """
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    roman = roman.upper()
    result = 0
    prev = 0

    for char in reversed(roman):
        curr = values.get(char, 0)
        if curr < prev:
            result -= curr
        else:
            result += curr
        prev = curr

    return result


def normalize_page_range(start: str, end: str) -> str:
    """Normalize page range to standard format.

    Args:
        start: Start page
        end: End page

    Returns:
        Normalized page range string
    """
    return f"{start}-{end}"


def is_valid_year(year: int) -> bool:
    """Check if year is in valid range for bibliographic records.

    Args:
        year: Year to validate

    Returns:
        True if valid
    """
    return 1500 <= year <= 2030
