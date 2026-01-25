"""Tests for validation and scoring modules."""

import pytest

from pdfhunter.models.bibliography import RecordStatus
from pdfhunter.validation.scorer import (
    ConfidenceScorer,
    DocumentType,
    FieldScore,
    ScoringResult,
    create_scorer,
)
from pdfhunter.validation.validator import (
    FieldValidator,
    RecordValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    create_validator,
)


# Validator Tests
class TestValidationIssue:
    def test_create_issue(self):
        issue = ValidationIssue(
            field_name="year",
            severity=ValidationSeverity.ERROR,
            message="Year is missing",
        )
        assert issue.field_name == "year"
        assert issue.severity == ValidationSeverity.ERROR

    def test_issue_with_suggestion(self):
        issue = ValidationIssue(
            field_name="pages",
            severity=ValidationSeverity.WARNING,
            message="Unusual format",
            suggestion="Use 123-456 format",
        )
        assert issue.suggestion == "Use 123-456 format"

    def test_issue_to_dict(self):
        issue = ValidationIssue(
            field_name="title",
            severity=ValidationSeverity.INFO,
            message="Title is short",
        )
        d = issue.to_dict()

        assert d["field_name"] == "title"
        assert d["severity"] == "info"
        assert d["message"] == "Title is short"


class TestValidationResult:
    def test_empty_result(self):
        result = ValidationResult()
        assert result.is_valid is True
        assert result.issues == []

    def test_add_warning(self):
        result = ValidationResult()
        result.add_issue("field", ValidationSeverity.WARNING, "warning message")

        assert result.is_valid is True  # Warnings don't make invalid
        assert result.has_warnings()
        assert not result.has_errors()

    def test_add_error(self):
        result = ValidationResult()
        result.add_issue("field", ValidationSeverity.ERROR, "error message")

        assert result.is_valid is False  # Errors make invalid
        assert result.has_errors()

    def test_get_issues_for_field(self):
        result = ValidationResult()
        result.add_issue("year", ValidationSeverity.ERROR, "missing")
        result.add_issue("year", ValidationSeverity.WARNING, "suspicious")
        result.add_issue("title", ValidationSeverity.INFO, "short")

        year_issues = result.get_issues_for_field("year")
        assert len(year_issues) == 2

        title_issues = result.get_issues_for_field("title")
        assert len(title_issues) == 1


class TestFieldValidator:
    def test_validate_year_valid(self):
        validator = FieldValidator()
        result = ValidationResult()
        validator.validate_year(2023, result)

        assert not result.has_errors()

    def test_validate_year_missing(self):
        validator = FieldValidator()
        result = ValidationResult()
        validator.validate_year(None, result)

        assert result.has_errors()

    def test_validate_year_too_early(self):
        validator = FieldValidator()
        result = ValidationResult()
        validator.validate_year(1400, result)

        assert result.has_errors()

    def test_validate_year_future(self):
        validator = FieldValidator()
        result = ValidationResult()
        validator.validate_year(2050, result)

        assert result.has_errors()

    def test_validate_pages_valid(self):
        validator = FieldValidator()
        result = ValidationResult()
        validator.validate_pages("123-456", result)

        assert not result.has_errors()

    def test_validate_pages_inverted(self):
        validator = FieldValidator()
        result = ValidationResult()
        validator.validate_pages("456-123", result)

        assert result.has_errors()

    def test_validate_title_valid(self):
        validator = FieldValidator()
        result = ValidationResult()
        validator.validate_title("A Study of Something Important", result)

        assert not result.has_errors()

    def test_validate_title_missing(self):
        validator = FieldValidator()
        result = ValidationResult()
        validator.validate_title(None, result)

        assert result.has_errors()

    def test_validate_title_too_short(self):
        validator = FieldValidator()
        result = ValidationResult()
        validator.validate_title("Hi", result)

        assert result.has_errors()

    def test_validate_authors_valid(self):
        validator = FieldValidator()
        result = ValidationResult()
        validator.validate_authors(
            [{"family": "Smith", "given": "John"}], result
        )

        assert not result.has_errors()

    def test_validate_authors_missing(self):
        validator = FieldValidator()
        result = ValidationResult()
        validator.validate_authors([], result)

        assert result.has_errors()

    def test_validate_doi_valid(self):
        validator = FieldValidator()
        result = ValidationResult()
        validator.validate_doi("10.1234/test.2023", result)

        assert not result.has_errors()

    def test_validate_doi_invalid(self):
        validator = FieldValidator()
        result = ValidationResult()
        validator.validate_doi("invalid-doi", result)

        assert result.has_errors()


class TestRecordValidator:
    def test_validate_complete_record(self):
        validator = RecordValidator()
        record = {
            "title": "A Complete Research Article",
            "authors": [{"family": "Smith", "given": "John"}],
            "year": 2023,
            "container_title": "Journal of Testing",
            "volume": "10",
            "issue": "2",
            "pages": "100-120",
        }
        result = validator.validate(record)

        assert result.is_valid

    def test_validate_minimal_record(self):
        validator = RecordValidator()
        record = {
            "title": "Minimal Record",
            "authors": [{"family": "Doe"}],
            "year": 2020,
        }
        result = validator.validate(record)

        assert result.is_valid

    def test_validate_missing_required(self):
        validator = RecordValidator()
        record = {
            "volume": "10",
            "pages": "1-10",
        }
        result = validator.validate(record)

        assert not result.is_valid
        assert result.has_errors()

    def test_create_validator_factory(self):
        validator = create_validator()
        assert isinstance(validator, RecordValidator)


# Scorer Tests
class TestFieldScore:
    def test_create_score(self):
        score = FieldScore(
            field_name="title",
            is_present=True,
            weight=0.35,
            score=1.0,
        )
        assert score.weighted_score() == 0.35

    def test_weighted_score_zero(self):
        score = FieldScore(
            field_name="doi",
            is_present=False,
            weight=0.5,
            score=0.0,
        )
        assert score.weighted_score() == 0.0


class TestScoringResult:
    def test_empty_result(self):
        result = ScoringResult()
        assert result.overall_score == 0.0
        assert result.status == RecordStatus.NEEDS_REVIEW

    def test_result_to_dict(self):
        result = ScoringResult(
            overall_score=0.85,
            status=RecordStatus.CONFIRMED,
            document_type=DocumentType.ARTICLE,
        )
        d = result.to_dict()

        assert d["overall_score"] == 0.85
        assert d["status"] == "confirmed"
        assert d["document_type"] == "article"


class TestConfidenceScorer:
    def test_score_complete_article(self):
        scorer = ConfidenceScorer()
        record = {
            "title": "A Complete Research Article About Something",
            "authors": [{"family": "Smith", "given": "John"}],
            "year": 2023,
            "container_title": "Journal of Testing",
            "volume": "10",
            "issue": "2",
            "pages": "100-120",
            "doi": "10.1234/test.2023",
        }
        result = scorer.score(record)

        assert result.overall_score >= 0.75
        assert result.status == RecordStatus.CONFIRMED

    def test_score_minimal_record(self):
        scorer = ConfidenceScorer()
        record = {
            "title": "A Minimal Record Title",
            "authors": [{"family": "Doe"}],
            "year": 2020,
        }
        result = scorer.score(record)

        assert 0.4 <= result.overall_score <= 0.8
        assert result.status == RecordStatus.NEEDS_REVIEW

    def test_score_empty_record(self):
        scorer = ConfidenceScorer()
        record = {}
        result = scorer.score(record)

        assert result.overall_score < 0.4
        assert result.status == RecordStatus.FAILED

    def test_score_book(self):
        scorer = ConfidenceScorer()
        record = {
            "title": "A Book About Something Important",
            "authors": [{"family": "Author", "given": "Book"}],
            "year": 2022,
            "publisher": "Publisher Name",
            "publisher_place": "New York",
            "isbn": "978-1234567890",
            "document_type": "book",
        }
        result = scorer.score(record)

        assert result.document_type == DocumentType.BOOK
        assert result.overall_score > 0.6

    def test_detect_article_type(self):
        scorer = ConfidenceScorer()
        record = {
            "title": "Article Title",
            "container_title": "Journal Name",
            "volume": "10",
        }
        result = scorer.score(record)

        assert result.document_type == DocumentType.ARTICLE

    def test_detect_book_type(self):
        scorer = ConfidenceScorer()
        record = {
            "title": "Book Title",
            "publisher": "Publisher",
            "isbn": "978-1234567890",
        }
        result = scorer.score(record)

        assert result.document_type == DocumentType.BOOK

    def test_custom_thresholds(self):
        scorer = ConfidenceScorer(
            confirmed_threshold=0.9,
            needs_review_threshold=0.5,
        )
        assert scorer.confirmed_threshold == 0.9
        assert scorer.needs_review_threshold == 0.5

    def test_create_scorer_factory(self):
        scorer = create_scorer()
        assert isinstance(scorer, ConfidenceScorer)

    def test_field_scores_populated(self):
        scorer = ConfidenceScorer()
        record = {
            "title": "Test Title",
            "year": 2023,
        }
        result = scorer.score(record)

        # Should have scores for all field categories
        assert len(result.field_scores) > 0

        # Find title score
        title_scores = [s for s in result.field_scores if s.field_name == "title"]
        assert len(title_scores) == 1
        assert title_scores[0].is_present is True

    def test_score_russian_record(self):
        scorer = ConfidenceScorer()
        record = {
            "title": "Исследование палеонтологических находок",
            "authors": [{"family": "Иванов", "given": "Иван"}],
            "year": 1985,
            "container_title": "Труды института",
            "volume": "15",
            "pages": "45-67",
        }
        result = scorer.score(record)

        assert result.overall_score >= 0.7
        assert result.status in [RecordStatus.CONFIRMED, RecordStatus.NEEDS_REVIEW]
