"""Rule-based extraction of bibliographic fields."""

from dataclasses import dataclass, field
from typing import Any

from pdfhunter.parsing.patterns import (
    COMPILED_DOI_PATTERNS,
    COMPILED_IDENTIFIER_PATTERNS,
    COMPILED_ISSUE_PATTERNS,
    COMPILED_PAGE_PATTERNS,
    COMPILED_PLACE_PATTERNS,
    COMPILED_SERIES_PATTERNS,
    COMPILED_VOLUME_PATTERNS,
    COMPILED_YEAR_PATTERNS,
    PatternMatch,
    is_valid_year,
    normalize_page_range,
    roman_to_int,
)


@dataclass
class ExtractionResult:
    """Result of rule-based extraction, containing all found matches and best values."""

    # Best extracted values for each field
    year: int | None = None
    pages: str | None = None
    volume: str | None = None
    issue: str | None = None
    series: str | None = None
    place: str | None = None
    doi: str | None = None
    issn: str | None = None
    isbn: str | None = None

    # All pattern matches found
    matches: list[PatternMatch] = field(default_factory=list)
    source_text: str = ""

    def field_count(self) -> int:
        """Count the number of non-None fields."""
        count = 0
        for field_name in ["year", "pages", "volume", "issue", "series", "place", "doi", "issn", "isbn"]:
            if getattr(self, field_name) is not None:
                count += 1
        return count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        for field_name in ["year", "pages", "volume", "issue", "series", "place", "doi", "issn", "isbn"]:
            value = getattr(self, field_name)
            if value is not None:
                result[field_name] = value
        return result

    def get_matches_for_field(self, field_name: str) -> list[PatternMatch]:
        """Get all matches for a specific field."""
        return [m for m in self.matches if m.field_name == field_name]


class RuleBasedExtractor:
    """Extract bibliographic fields using regex patterns."""

    def __init__(
        self,
        extract_all_matches: bool = True,
        min_confidence: float = 0.5,
    ):
        """Initialize the extractor.

        Args:
            extract_all_matches: If True, store all matches. If False, only keep best.
            min_confidence: Minimum confidence threshold for matches.
        """
        self.extract_all_matches = extract_all_matches
        self.min_confidence = min_confidence

    def extract(self, text: str, page_number: int | None = None) -> ExtractionResult:
        """Extract all possible bibliographic fields from text.

        Args:
            text: Text to extract from.
            page_number: The page number where the text originated.

        Returns:
            ExtractionResult with extracted values and all found pattern matches.
        """
        result = ExtractionResult(source_text=text)

        # Extract all field types and add all matches to the result
        self._extract_year(text, page_number, result)
        self._extract_pages(text, page_number, result)
        self._extract_volume(text, page_number, result)
        self._extract_issue(text, page_number, result)
        self._extract_series(text, page_number, result)
        self._extract_place(text, page_number, result)
        self._extract_doi(text, page_number, result)
        self._extract_identifiers(text, page_number, result)

        # Set best values for each field based on confidence
        self._set_best_values(result)

        return result

    def _set_best_values(self, result: ExtractionResult) -> None:
        """Set the best value for each field based on confidence."""
        field_map = {
            "year": "year",
            "pages": "pages",
            "volume": "volume",
            "issue": "issue",
            "series": "series",
            "place": "place",
            "doi": "doi",
            "issn": "issn",
            "isbn": "isbn",
            "isbn13": "isbn",  # Map isbn13 to isbn
            "isbn10": "isbn",  # Map isbn10 to isbn
        }

        for match_field, result_field in field_map.items():
            matches = [m for m in result.matches if m.field_name == match_field and m.confidence >= self.min_confidence]
            if matches:
                # Skip if result field already set (prefer isbn13 over isbn10)
                if getattr(result, result_field) is not None:
                    continue
                best_match = max(matches, key=lambda m: m.confidence)
                value = best_match.value
                # Convert year to int
                if match_field == "year":
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        continue
                setattr(result, result_field, value)

    def _extract_year(self, text: str, page_number: int | None, result: ExtractionResult) -> None:
        """Find all year patterns."""
        for pattern, pattern_name in COMPILED_YEAR_PATTERNS:
            for match in pattern.finditer(text):
                year_str = match.group(1)
                try:
                    year = int(year_str)
                except ValueError:
                    continue

                if not is_valid_year(year):
                    continue

                confidence = self._calculate_year_confidence(pattern_name, text, match)

                result.matches.append(PatternMatch(
                    field_name="year",
                    value=str(year),
                    raw_match=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=confidence,
                    pattern_name=pattern_name,
                    page_number=page_number,
                ))

    def _calculate_year_confidence(self, pattern_name: str, text: str, match) -> float:
        """Calculate confidence for a year match."""
        confidence = 0.8
        if pattern_name == "year_copyright":
            confidence = 0.95
        if pattern_name == "year_parentheses":
            confidence = 0.9
        context_start = max(0, match.start() - 20)
        context = text[context_start:match.end() + 20].lower()
        if any(word in context for word in ["published", "copyright", "©", "année", "год"]):
            confidence = min(1.0, confidence + 0.1)
        if any(word in context for word in ["p.", "pp.", "page", "vol"]):
            confidence = max(0.3, confidence - 0.3)
        return confidence

    def _extract_pages(self, text: str, page_number: int | None, result: ExtractionResult) -> None:
        """Find all page range patterns."""
        for pattern, pattern_name in COMPILED_PAGE_PATTERNS:
            for match in pattern.finditer(text):
                groups = match.groups()
                pages = normalize_page_range(groups[0], groups[1]) if len(groups) >= 2 and groups[1] else groups[0]
                confidence = 0.9 if len(groups) >= 2 and groups[1] else 0.7

                result.matches.append(PatternMatch(
                    field_name="pages",
                    value=pages,
                    raw_match=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=confidence,
                    pattern_name=pattern_name,
                    page_number=page_number,
                ))

    def _extract_volume(self, text: str, page_number: int | None, result: ExtractionResult) -> None:
        """Find all volume patterns."""
        for pattern, pattern_name in COMPILED_VOLUME_PATTERNS:
            for match in pattern.finditer(text):
                volume = match.group(1)
                if volume.upper().replace("I", "").replace("V", "").replace("X", "").replace("L", "").replace("C", "").replace("D", "").replace("M", "") == "":
                    try:
                        volume = str(roman_to_int(volume))
                    except Exception:
                        pass

                result.matches.append(PatternMatch(
                    field_name="volume",
                    value=volume,
                    raw_match=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.85,
                    pattern_name=pattern_name,
                    page_number=page_number,
                ))

    def _extract_issue(self, text: str, page_number: int | None, result: ExtractionResult) -> None:
        """Find all issue number patterns."""
        for pattern, pattern_name in COMPILED_ISSUE_PATTERNS:
            for match in pattern.finditer(text):
                result.matches.append(PatternMatch(
                    field_name="issue",
                    value=match.group(1),
                    raw_match=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.85,
                    pattern_name=pattern_name,
                    page_number=page_number,
                ))

    def _extract_series(self, text: str, page_number: int | None, result: ExtractionResult) -> None:
        """Find all series information patterns."""
        for pattern, pattern_name in COMPILED_SERIES_PATTERNS:
            for match in pattern.finditer(text):
                result.matches.append(PatternMatch(
                    field_name="series",
                    value=match.groups()[0] if match.groups() else match.group(0),
                    raw_match=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.8,
                    pattern_name=pattern_name,
                    page_number=page_number,
                ))

    def _extract_place(self, text: str, page_number: int | None, result: ExtractionResult) -> None:
        """Find all publication place patterns."""
        for pattern, pattern_name in COMPILED_PLACE_PATTERNS:
            for match in pattern.finditer(text):
                confidence = 0.9 if pattern_name in ["place_major", "place_major2"] else 0.75
                result.matches.append(PatternMatch(
                    field_name="place",
                    value=match.group(1),
                    raw_match=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=confidence,
                    pattern_name=pattern_name,
                    page_number=page_number,
                ))

    def _extract_doi(self, text: str, page_number: int | None, result: ExtractionResult) -> None:
        """Find all DOI patterns."""
        for pattern, pattern_name in COMPILED_DOI_PATTERNS:
            for match in pattern.finditer(text):
                result.matches.append(PatternMatch(
                    field_name="doi",
                    value=match.group(1),
                    raw_match=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.95,
                    pattern_name=pattern_name,
                    page_number=page_number,
                ))

    def _extract_identifiers(self, text: str, page_number: int | None, result: ExtractionResult) -> None:
        """Find all ISSN/ISBN patterns."""
        for pattern, pattern_name in COMPILED_IDENTIFIER_PATTERNS:
            for match in pattern.finditer(text):
                result.matches.append(PatternMatch(
                    field_name=pattern_name,
                    value=match.group(1).replace("–", "-").replace(" ", ""),
                    raw_match=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.95,
                    pattern_name=pattern_name,
                    page_number=page_number,
                ))


def create_rule_based_extractor(
    extract_all_matches: bool = True,
    min_confidence: float = 0.5,
) -> RuleBasedExtractor:
    """Factory function to create a RuleBasedExtractor.

    Args:
        extract_all_matches: If True, store all matches. If False, only keep best.
        min_confidence: Minimum confidence threshold for matches.

    Returns:
        A configured RuleBasedExtractor instance.
    """
    return RuleBasedExtractor(
        extract_all_matches=extract_all_matches,
        min_confidence=min_confidence,
    )
