"""Tests for data models."""

import pytest

from pdfresolve.models.bibliography import (
    Author,
    BibliographyRecord,
    DateParts,
    RecordStatus,
)
from pdfresolve.models.evidence import BoundingBox, Evidence, EvidenceType


class TestAuthor:
    def test_author_with_family_given(self):
        author = Author(family="Smith", given="John")
        csl = author.to_csl()
        assert csl == {"family": "Smith", "given": "John"}

    def test_author_with_literal(self):
        author = Author(literal="Anonymous")
        csl = author.to_csl()
        assert csl == {"literal": "Anonymous"}

    def test_author_family_only(self):
        author = Author(family="Smith")
        csl = author.to_csl()
        assert csl == {"family": "Smith"}


class TestDateParts:
    def test_full_date(self):
        date = DateParts(year=2024, month=1, day=15)
        csl = date.to_csl()
        assert csl == {"date-parts": [[2024, 1, 15]]}

    def test_year_month(self):
        date = DateParts(year=2024, month=6)
        csl = date.to_csl()
        assert csl == {"date-parts": [[2024, 6]]}

    def test_year_only(self):
        date = DateParts(year=1999)
        csl = date.to_csl()
        assert csl == {"date-parts": [[1999]]}

    def test_empty_date(self):
        date = DateParts()
        csl = date.to_csl()
        assert csl == {}


class TestBibliographyRecord:
    def test_minimal_record(self):
        record = BibliographyRecord(id="test-1")
        assert record.id == "test-1"
        assert record.type == "article"
        assert record.status == RecordStatus.NEEDS_REVIEW

    def test_to_csl_json(self):
        record = BibliographyRecord(
            id="test-2",
            type="article-journal",
            title="Test Article",
            author=[Author(family="Doe", given="Jane")],
            issued=DateParts(year=2023),
            container_title="Test Journal",
            volume="10",
            issue="2",
            page="100-110",
        )
        csl = record.to_csl_json()

        assert csl["id"] == "test-2"
        assert csl["type"] == "article-journal"
        assert csl["title"] == "Test Article"
        assert csl["author"] == [{"family": "Doe", "given": "Jane"}]
        assert csl["issued"] == {"date-parts": [[2023]]}
        assert csl["container-title"] == "Test Journal"
        assert csl["volume"] == "10"
        assert csl["issue"] == "2"
        assert csl["page"] == "100-110"

    def test_calculate_confidence(self):
        # Record with all required fields
        record = BibliographyRecord(
            id="test-3",
            title="Test",
            author=[Author(family="Test")],
            issued=DateParts(year=2020),
        )
        confidence = record.calculate_confidence()
        assert confidence >= 0.6  # Required fields present

    def test_determine_status_confirmed(self):
        record = BibliographyRecord(
            id="test-4",
            title="Test Article",
            author=[Author(family="Doe")],
            issued=DateParts(year=2023),
            container_title="Journal",
            volume="1",
            page="1-10",
            publisher="Publisher",
        )
        status = record.determine_status()
        assert status == RecordStatus.CONFIRMED

    def test_determine_status_needs_review(self):
        record = BibliographyRecord(
            id="test-5",
            title="Test",
            author=[Author(family="Doe")],
        )
        status = record.determine_status()
        assert status == RecordStatus.NEEDS_REVIEW

    def test_determine_status_failed(self):
        record = BibliographyRecord(id="test-6")
        status = record.determine_status()
        assert status == RecordStatus.FAILED


class TestEvidence:
    def test_basic_evidence(self):
        evidence = Evidence(
            field_name="title",
            evidence_type=EvidenceType.OCR_TEXT,
            page_number=1,
            source_text="Test Title",
            confidence=0.95,
        )
        assert evidence.field_name == "title"
        assert evidence.page_number == 1

    def test_evidence_with_bbox(self):
        bbox = BoundingBox(x1=10, y1=20, x2=100, y2=40)
        evidence = Evidence(
            field_name="year",
            evidence_type=EvidenceType.OCR_TEXT,
            bbox=bbox,
        )
        assert evidence.bbox.to_list() == [10, 20, 100, 40]

    def test_evidence_to_dict(self):
        evidence = Evidence(
            field_name="author",
            evidence_type=EvidenceType.PDF_TEXT,
            page_number=1,
            source_text="John Doe",
            confidence=0.9,
        )
        d = evidence.to_dict()

        assert d["field_name"] == "author"
        assert d["evidence_type"] == "pdf_text"
        assert d["page_number"] == 1
        assert d["source_text"] == "John Doe"
        assert d["confidence"] == 0.9
