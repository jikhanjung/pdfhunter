"""Confidence scoring for bibliographic records."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pdfhunter.models.bibliography import RecordStatus


class DocumentType(str, Enum):
    """Document type for scoring purposes."""

    ARTICLE = "article"
    BOOK = "book"
    CHAPTER = "chapter"
    REPORT = "report"
    THESIS = "thesis"
    PROCEEDINGS = "proceedings"
    UNKNOWN = "unknown"


@dataclass
class FieldScore:
    """Score for a single field."""

    field_name: str
    is_present: bool
    weight: float
    score: float  # 0-1
    notes: str = ""

    def weighted_score(self) -> float:
        """Get weighted score."""
        return self.score * self.weight


@dataclass
class ScoringResult:
    """Result of confidence scoring."""

    overall_score: float = 0.0
    status: RecordStatus = RecordStatus.NEEDS_REVIEW
    field_scores: list[FieldScore] = field(default_factory=list)
    document_type: DocumentType = DocumentType.UNKNOWN

    # Score breakdown
    required_score: float = 0.0
    structure_score: float = 0.0
    publication_score: float = 0.0
    identifier_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall_score": round(self.overall_score, 3),
            "status": self.status.value,
            "document_type": self.document_type.value,
            "breakdown": {
                "required": round(self.required_score, 3),
                "structure": round(self.structure_score, 3),
                "publication": round(self.publication_score, 3),
                "identifier": round(self.identifier_score, 3),
            },
            "field_scores": [
                {
                    "field": fs.field_name,
                    "present": fs.is_present,
                    "score": round(fs.score, 3),
                    "weighted": round(fs.weighted_score(), 3),
                }
                for fs in self.field_scores
            ],
        }


class ConfidenceScorer:
    """Calculate confidence scores for bibliographic records."""

    # Field weights by category
    REQUIRED_FIELDS = {
        "title": 0.35,
        "authors": 0.35,
        "year": 0.30,
    }

    STRUCTURE_FIELDS = {
        "container_title": 0.30,
        "volume": 0.25,
        "issue": 0.20,
        "pages": 0.25,
    }

    PUBLICATION_FIELDS = {
        "publisher": 0.50,
        "publisher_place": 0.50,
    }

    IDENTIFIER_FIELDS = {
        "doi": 0.50,
        "issn": 0.25,
        "isbn": 0.25,
    }

    # Category weights
    CATEGORY_WEIGHTS = {
        "required": 0.50,
        "structure": 0.25,
        "publication": 0.15,
        "identifier": 0.10,
    }

    # Status thresholds
    CONFIRMED_THRESHOLD = 0.75
    NEEDS_REVIEW_THRESHOLD = 0.40

    def __init__(
        self,
        confirmed_threshold: float | None = None,
        needs_review_threshold: float | None = None,
    ):
        """Initialize scorer.

        Args:
            confirmed_threshold: Score threshold for confirmed status
            needs_review_threshold: Score threshold for needs_review status
        """
        self.confirmed_threshold = confirmed_threshold or self.CONFIRMED_THRESHOLD
        self.needs_review_threshold = needs_review_threshold or self.NEEDS_REVIEW_THRESHOLD

    def score(self, record: dict[str, Any]) -> ScoringResult:
        """Calculate confidence score for a record.

        Args:
            record: Dictionary with bibliographic fields

        Returns:
            ScoringResult with scores and status
        """
        result = ScoringResult()

        # Detect document type
        result.document_type = self._detect_document_type(record)

        # Score each category
        result.required_score = self._score_category(
            record, self.REQUIRED_FIELDS, result.field_scores
        )
        result.structure_score = self._score_category(
            record, self.STRUCTURE_FIELDS, result.field_scores
        )
        result.publication_score = self._score_category(
            record, self.PUBLICATION_FIELDS, result.field_scores
        )
        result.identifier_score = self._score_category(
            record, self.IDENTIFIER_FIELDS, result.field_scores
        )

        # Calculate overall score
        result.overall_score = (
            result.required_score * self.CATEGORY_WEIGHTS["required"]
            + result.structure_score * self.CATEGORY_WEIGHTS["structure"]
            + result.publication_score * self.CATEGORY_WEIGHTS["publication"]
            + result.identifier_score * self.CATEGORY_WEIGHTS["identifier"]
        )

        # Adjust for document type
        result.overall_score = self._adjust_for_document_type(
            result.overall_score, record, result.document_type
        )

        # Determine status
        result.status = self._determine_status(result.overall_score)

        return result

    def _score_category(
        self,
        record: dict[str, Any],
        fields: dict[str, float],
        field_scores: list[FieldScore],
    ) -> float:
        """Score a category of fields.

        Args:
            record: Record dictionary
            fields: Dict of field_name -> weight
            field_scores: List to append field scores to

        Returns:
            Category score (0-1)
        """
        total_weight = sum(fields.values())
        weighted_sum = 0.0

        for field_name, weight in fields.items():
            value = record.get(field_name)
            is_present = self._is_field_present(value)
            score = self._score_field(field_name, value)

            field_score = FieldScore(
                field_name=field_name,
                is_present=is_present,
                weight=weight,
                score=score,
            )
            field_scores.append(field_score)

            weighted_sum += score * weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _is_field_present(self, value: Any) -> bool:
        """Check if a field value is present."""
        if value is None:
            return False
        if isinstance(value, str) and len(value.strip()) == 0:
            return False
        if isinstance(value, list) and len(value) == 0:
            return False
        return True

    def _score_field(self, field_name: str, value: Any) -> float:
        """Score a single field.

        Args:
            field_name: Name of the field
            value: Field value

        Returns:
            Score (0-1)
        """
        if not self._is_field_present(value):
            return 0.0

        # Base score for presence
        score = 1.0

        # Field-specific scoring
        if field_name == "title":
            score = self._score_title(value)
        elif field_name == "authors":
            score = self._score_authors(value)
        elif field_name == "year":
            score = self._score_year(value)
        elif field_name == "pages":
            score = self._score_pages(value)

        return score

    def _score_title(self, title: str) -> float:
        """Score title field."""
        if len(title) < 5:
            return 0.3
        elif len(title) < 15:
            return 0.7
        elif len(title) > 500:
            return 0.8  # Might include extra text
        return 1.0

    def _score_authors(self, authors: list) -> float:
        """Score authors field."""
        if not authors:
            return 0.0

        # Check quality of author entries
        valid_authors = 0
        for author in authors:
            if isinstance(author, dict):
                if author.get("family") or author.get("literal"):
                    valid_authors += 1

        if valid_authors == 0:
            return 0.0
        elif valid_authors < len(authors):
            return 0.7  # Some authors have issues
        return 1.0

    def _score_year(self, year: int) -> float:
        """Score year field."""
        if not isinstance(year, int):
            try:
                year = int(year)
            except (ValueError, TypeError):
                return 0.3

        if 1800 <= year <= 2030:
            return 1.0
        elif 1500 <= year < 1800:
            return 0.8  # Historical
        else:
            return 0.3  # Suspicious

    def _score_pages(self, pages: str) -> float:
        """Score pages field."""
        import re

        # Check format
        if re.match(r"^\d+(-\d+)?$", pages.replace("–", "-").replace("—", "-")):
            return 1.0
        return 0.7  # Non-standard format

    def _detect_document_type(self, record: dict[str, Any]) -> DocumentType:
        """Detect document type from record."""
        explicit_type = record.get("document_type", "").lower()

        if explicit_type:
            type_map = {
                "article": DocumentType.ARTICLE,
                "book": DocumentType.BOOK,
                "chapter": DocumentType.CHAPTER,
                "report": DocumentType.REPORT,
                "thesis": DocumentType.THESIS,
                "proceedings": DocumentType.PROCEEDINGS,
            }
            return type_map.get(explicit_type, DocumentType.UNKNOWN)

        # Infer from fields
        if record.get("container_title") and record.get("volume"):
            return DocumentType.ARTICLE
        if record.get("publisher") and not record.get("container_title"):
            return DocumentType.BOOK
        if record.get("isbn"):
            return DocumentType.BOOK

        return DocumentType.UNKNOWN

    def _adjust_for_document_type(
        self,
        score: float,
        record: dict[str, Any],
        doc_type: DocumentType,
    ) -> float:
        """Adjust score based on document type.

        Different document types have different required fields.
        """
        # Books don't need container_title, volume, issue, pages
        if doc_type == DocumentType.BOOK:
            if not record.get("container_title"):
                # Don't penalize books for missing journal info
                score = min(1.0, score + 0.05)

        # Articles need container info
        if doc_type == DocumentType.ARTICLE:
            if not record.get("container_title"):
                score = max(0.0, score - 0.10)

        return score

    def _determine_status(self, score: float) -> RecordStatus:
        """Determine record status from score."""
        if score >= self.confirmed_threshold:
            return RecordStatus.CONFIRMED
        elif score >= self.needs_review_threshold:
            return RecordStatus.NEEDS_REVIEW
        else:
            return RecordStatus.FAILED


def create_scorer(
    confirmed_threshold: float | None = None,
    needs_review_threshold: float | None = None,
) -> ConfidenceScorer:
    """Factory function to create a confidence scorer.

    Args:
        confirmed_threshold: Score threshold for confirmed status
        needs_review_threshold: Score threshold for needs_review status

    Returns:
        ConfidenceScorer instance
    """
    return ConfidenceScorer(
        confirmed_threshold=confirmed_threshold,
        needs_review_threshold=needs_review_threshold,
    )
