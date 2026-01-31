"""Field validation for bibliographic records."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValidationSeverity(str, Enum):
    """Severity level of validation issues."""

    ERROR = "error"  # Critical issue, field likely wrong
    WARNING = "warning"  # Possible issue, needs review
    INFO = "info"  # Minor issue or suggestion


@dataclass
class ValidationIssue:
    """A single validation issue."""

    field_name: str
    severity: ValidationSeverity
    message: str
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "field_name": self.field_name,
            "severity": self.severity.value,
            "message": self.message,
        }
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


@dataclass
class ValidationResult:
    """Result of validation."""

    is_valid: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)
    fields_validated: list[str] = field(default_factory=list)

    def add_issue(
        self,
        field_name: str,
        severity: ValidationSeverity,
        message: str,
        suggestion: str | None = None,
    ) -> None:
        """Add a validation issue."""
        self.issues.append(
            ValidationIssue(
                field_name=field_name,
                severity=severity,
                message=message,
                suggestion=suggestion,
            )
        )
        if severity == ValidationSeverity.ERROR:
            self.is_valid = False

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return any(i.severity == ValidationSeverity.WARNING for i in self.issues)

    def get_issues_for_field(self, field_name: str) -> list[ValidationIssue]:
        """Get all issues for a specific field."""
        return [i for i in self.issues if i.field_name == field_name]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues],
            "fields_validated": self.fields_validated,
        }


class FieldValidator:
    """Validator for individual bibliographic fields."""

    def __init__(self):
        """Initialize validator."""
        # Common journal abbreviations
        self.journal_abbreviations = {
            "Bull.", "J.", "Rev.", "Ann.", "Proc.", "Trans.", "Mem.",
            "Acta", "C. R.", "Z.", "Zt.", "Изв.", "Тр.", "Зап.",
        }

    def validate_year(self, year: int | None, result: ValidationResult) -> None:
        """Validate year field."""
        result.fields_validated.append("year")

        if year is None:
            result.add_issue(
                "year",
                ValidationSeverity.ERROR,
                "Year is missing",
            )
            return

        if year < 1500:
            result.add_issue(
                "year",
                ValidationSeverity.ERROR,
                f"Year {year} is too early for bibliographic record",
                suggestion="Check if this is actually a page number or other data",
            )
        elif year < 1800:
            result.add_issue(
                "year",
                ValidationSeverity.WARNING,
                f"Year {year} is unusually early",
                suggestion="Verify this is correct for historical documents",
            )
        elif year > 2030:
            result.add_issue(
                "year",
                ValidationSeverity.ERROR,
                f"Year {year} is in the future",
            )

    def validate_pages(self, pages: str | None, result: ValidationResult) -> None:
        """Validate pages field."""
        result.fields_validated.append("pages")

        if pages is None:
            # Pages are optional for some document types
            return

        # Check format
        if not re.match(r"^\d+(-\d+)?$", pages.replace("–", "-").replace("—", "-")):
            result.add_issue(
                "pages",
                ValidationSeverity.WARNING,
                f"Unusual page format: {pages}",
                suggestion="Expected format: 123 or 123-456",
            )
            return

        # Check range validity
        parts = pages.replace("–", "-").replace("—", "-").split("-")
        if len(parts) == 2:
            try:
                start, end = int(parts[0]), int(parts[1])
                if start > end:
                    result.add_issue(
                        "pages",
                        ValidationSeverity.ERROR,
                        f"Page range is inverted: {start} > {end}",
                        suggestion=f"Should be {end}-{start}",
                    )
                elif end - start > 500:
                    result.add_issue(
                        "pages",
                        ValidationSeverity.WARNING,
                        f"Page range is unusually large: {end - start + 1} pages",
                    )
            except ValueError:
                pass

    def validate_volume(self, volume: str | None, result: ValidationResult) -> None:
        """Validate volume field."""
        result.fields_validated.append("volume")

        if volume is None:
            return

        # Check if it looks like a valid volume
        if not re.match(r"^[\dIVXLCDM]+$", volume, re.IGNORECASE):
            result.add_issue(
                "volume",
                ValidationSeverity.INFO,
                f"Volume has unusual format: {volume}",
            )

        # Check for very high numbers
        try:
            vol_num = int(volume)
            if vol_num > 500:
                result.add_issue(
                    "volume",
                    ValidationSeverity.WARNING,
                    f"Volume number {vol_num} is unusually high",
                )
        except ValueError:
            pass  # Non-numeric volume is OK

    def validate_issue(self, issue: str | None, result: ValidationResult) -> None:
        """Validate issue field."""
        result.fields_validated.append("issue")

        if issue is None:
            return

        try:
            issue_num = int(issue)
            if issue_num > 100:
                result.add_issue(
                    "issue",
                    ValidationSeverity.WARNING,
                    f"Issue number {issue_num} is unusually high",
                )
        except ValueError:
            pass

    def validate_title(self, title: str | None, result: ValidationResult) -> None:
        """Validate title field."""
        result.fields_validated.append("title")

        if title is None:
            result.add_issue(
                "title",
                ValidationSeverity.ERROR,
                "Title is missing",
            )
            return

        if len(title) < 5:
            result.add_issue(
                "title",
                ValidationSeverity.ERROR,
                f"Title is too short: '{title}'",
            )
        elif len(title) < 15:
            result.add_issue(
                "title",
                ValidationSeverity.WARNING,
                f"Title seems short: '{title}'",
            )

        if len(title) > 500:
            result.add_issue(
                "title",
                ValidationSeverity.WARNING,
                "Title is unusually long",
                suggestion="Check if abstract or other text was included",
            )

        # Check for common OCR artifacts
        if re.search(r"[|}{\\]", title):
            result.add_issue(
                "title",
                ValidationSeverity.WARNING,
                "Title may contain OCR artifacts",
            )

    def validate_authors(
        self, authors: list[dict[str, str]] | None, result: ValidationResult
    ) -> None:
        """Validate authors field."""
        result.fields_validated.append("authors")

        if authors is None or len(authors) == 0:
            result.add_issue(
                "authors",
                ValidationSeverity.ERROR,
                "No authors found",
            )
            return

        for i, author in enumerate(authors):
            # Check for empty names
            family = author.get("family", "")
            given = author.get("given", "")
            literal = author.get("literal", "")

            if not family and not literal:
                result.add_issue(
                    "authors",
                    ValidationSeverity.ERROR,
                    f"Author {i + 1} has no family name or literal name",
                )
                continue

            name = literal or family

            # Check for suspicious patterns
            if re.match(r"^\d+$", name):
                result.add_issue(
                    "authors",
                    ValidationSeverity.ERROR,
                    f"Author name '{name}' appears to be a number",
                )

            if len(name) < 2:
                result.add_issue(
                    "authors",
                    ValidationSeverity.WARNING,
                    f"Author name '{name}' is very short",
                )

    def validate_container_title(
        self, container_title: str | None, result: ValidationResult
    ) -> None:
        """Validate container title (journal/book name)."""
        result.fields_validated.append("container_title")

        if container_title is None:
            # Optional for books
            return

        if len(container_title) < 3:
            result.add_issue(
                "container_title",
                ValidationSeverity.WARNING,
                f"Container title is very short: '{container_title}'",
            )

    def validate_doi(self, doi: str | None, result: ValidationResult) -> None:
        """Validate DOI format."""
        result.fields_validated.append("doi")

        if doi is None:
            return

        if not re.match(r"^10\.\d{4,}/", doi):
            result.add_issue(
                "doi",
                ValidationSeverity.ERROR,
                f"Invalid DOI format: {doi}",
                suggestion="DOI should start with '10.XXXX/'",
            )

    def validate_issn(self, issn: str | None, result: ValidationResult) -> None:
        """Validate ISSN format."""
        result.fields_validated.append("issn")

        if issn is None:
            return

        # Remove hyphens and check format
        clean = issn.replace("-", "")
        if not re.match(r"^\d{7}[\dXx]$", clean):
            result.add_issue(
                "issn",
                ValidationSeverity.ERROR,
                f"Invalid ISSN format: {issn}",
                suggestion="ISSN should be XXXX-XXXX format",
            )


class RecordValidator:
    """Validator for complete bibliographic records."""

    def __init__(self):
        """Initialize record validator."""
        self.field_validator = FieldValidator()

    def validate(self, record: dict[str, Any]) -> ValidationResult:
        """Validate a bibliographic record.

        Args:
            record: Dictionary with bibliographic fields

        Returns:
            ValidationResult with all issues found
        """
        result = ValidationResult()

        # Validate individual fields
        self.field_validator.validate_year(record.get("year"), result)
        self.field_validator.validate_title(record.get("title"), result)
        self.field_validator.validate_authors(record.get("authors"), result)
        self.field_validator.validate_pages(record.get("pages"), result)
        self.field_validator.validate_volume(record.get("volume"), result)
        self.field_validator.validate_issue(record.get("issue"), result)
        self.field_validator.validate_container_title(
            record.get("container_title"), result
        )
        self.field_validator.validate_doi(record.get("doi"), result)
        self.field_validator.validate_issn(record.get("issn"), result)

        # Cross-field validation
        self._validate_cross_field(record, result)

        return result

    def _validate_cross_field(
        self, record: dict[str, Any], result: ValidationResult
    ) -> None:
        """Perform cross-field validation."""
        doc_type = record.get("document_type", "article")

        # Journal articles should have container_title
        if doc_type == "article" and not record.get("container_title"):
            result.add_issue(
                "container_title",
                ValidationSeverity.WARNING,
                "Journal articles should have a container title (journal name)",
            )

        # Books should have publisher
        if doc_type == "book" and not record.get("publisher"):
            result.add_issue(
                "publisher",
                ValidationSeverity.INFO,
                "Books typically have a publisher",
            )

        # Check year-page consistency (pages shouldn't look like years)
        pages = record.get("pages")
        year = record.get("year")
        if pages and year:
            try:
                page_parts = pages.replace("–", "-").replace("—", "-").split("-")
                for part in page_parts:
                    page_num = int(part)
                    if 1900 <= page_num <= 2030 and page_num != year:
                        result.add_issue(
                            "pages",
                            ValidationSeverity.INFO,
                            f"Page number {page_num} looks like a year",
                        )
            except ValueError:
                pass


def create_validator() -> RecordValidator:
    """Factory function to create a record validator.

    Returns:
        RecordValidator instance
    """
    return RecordValidator()
