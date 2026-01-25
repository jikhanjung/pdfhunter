"""Tests for export modules."""

import json
import pytest
from pathlib import Path

from pdfhunter.models.bibliography import (
    Author,
    BibliographyRecord,
    DateParts,
)
from pdfhunter.export.csl_json import (
    export_csl_json,
    export_csl_json_string,
    load_csl_json,
    record_to_csl_json,
    records_to_csl_json,
)
from pdfhunter.export.ris import (
    export_ris,
    export_ris_string,
    record_to_ris,
    records_to_ris,
)
from pdfhunter.export.bibtex import (
    escape_bibtex,
    export_bibtex,
    export_bibtex_string,
    generate_cite_key,
    record_to_bibtex,
    records_to_bibtex,
)


@pytest.fixture
def sample_article():
    """Create a sample article record."""
    return BibliographyRecord(
        id="smith2023",
        type="article-journal",
        title="A Study of Something Important",
        author=[
            Author(family="Smith", given="John"),
            Author(family="Doe", given="Jane"),
        ],
        issued=DateParts(year=2023, month=6),
        container_title="Journal of Testing",
        volume="10",
        issue="2",
        page="100-120",
        doi="10.1234/test.2023",
        language="en",
    )


@pytest.fixture
def sample_book():
    """Create a sample book record."""
    return BibliographyRecord(
        id="author2022",
        type="book",
        title="A Complete Book Title",
        author=[Author(family="Author", given="Book")],
        issued=DateParts(year=2022),
        publisher="Academic Press",
        publisher_place="New York",
        isbn="978-1234567890",
    )


@pytest.fixture
def sample_russian():
    """Create a sample Russian record."""
    return BibliographyRecord(
        id="ivanov1985",
        type="article",
        title="Исследование палеонтологических находок",
        author=[Author(family="Иванов", given="Иван")],
        issued=DateParts(year=1985),
        container_title="Труды института",
        volume="15",
        page="45-67",
        language="ru",
    )


# CSL-JSON Tests
class TestCSLJSON:
    def test_record_to_csl_json(self, sample_article):
        csl = record_to_csl_json(sample_article)

        assert csl["id"] == "smith2023"
        assert csl["type"] == "article-journal"
        assert csl["title"] == "A Study of Something Important"
        assert len(csl["author"]) == 2
        assert csl["author"][0]["family"] == "Smith"
        assert csl["container-title"] == "Journal of Testing"
        assert csl["volume"] == "10"
        assert csl["DOI"] == "10.1234/test.2023"

    def test_records_to_csl_json(self, sample_article, sample_book):
        csl_list = records_to_csl_json([sample_article, sample_book])

        assert len(csl_list) == 2
        assert csl_list[0]["id"] == "smith2023"
        assert csl_list[1]["id"] == "author2022"

    def test_export_csl_json_string(self, sample_article):
        json_str = export_csl_json_string(sample_article)

        data = json.loads(json_str)
        assert len(data) == 1
        assert data[0]["id"] == "smith2023"

    def test_export_csl_json_file(self, sample_article, tmp_path):
        output_file = tmp_path / "test.json"
        export_csl_json(sample_article, output_file)

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert len(data) == 1

    def test_load_csl_json(self, sample_article, tmp_path):
        output_file = tmp_path / "test.json"
        export_csl_json(sample_article, output_file)

        loaded = load_csl_json(output_file)
        assert len(loaded) == 1
        assert loaded[0]["id"] == "smith2023"

    def test_csl_json_cyrillic(self, sample_russian):
        json_str = export_csl_json_string(sample_russian, ensure_ascii=False)

        assert "Иванов" in json_str
        assert "Исследование" in json_str


# RIS Tests
class TestRIS:
    def test_record_to_ris(self, sample_article):
        ris = record_to_ris(sample_article)

        assert "TY  - JOUR" in ris
        assert "ID  - smith2023" in ris
        assert "TI  - A Study of Something Important" in ris
        assert "AU  - Smith, John" in ris
        assert "AU  - Doe, Jane" in ris
        assert "PY  - 2023" in ris
        assert "JO  - Journal of Testing" in ris
        assert "VL  - 10" in ris
        assert "IS  - 2" in ris
        assert "SP  - 100" in ris
        assert "EP  - 120" in ris
        assert "DO  - 10.1234/test.2023" in ris
        assert "ER  - " in ris

    def test_record_to_ris_book(self, sample_book):
        ris = record_to_ris(sample_book)

        assert "TY  - BOOK" in ris
        assert "PB  - Academic Press" in ris
        assert "CY  - New York" in ris
        assert "SN  - 978-1234567890" in ris

    def test_records_to_ris(self, sample_article, sample_book):
        ris = records_to_ris([sample_article, sample_book])

        # Should have two separate records
        assert ris.count("TY  - ") == 2
        assert ris.count("ER  - ") == 2

    def test_export_ris_string(self, sample_article):
        ris = export_ris_string(sample_article)

        assert "TY  - JOUR" in ris
        assert "ER  - " in ris

    def test_export_ris_file(self, sample_article, tmp_path):
        output_file = tmp_path / "test.ris"
        export_ris(sample_article, output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "TY  - JOUR" in content

    def test_ris_cyrillic(self, sample_russian):
        ris = export_ris_string(sample_russian)

        assert "AU  - Иванов, Иван" in ris
        assert "Исследование" in ris


# BibTeX Tests
class TestBibTeX:
    def test_escape_bibtex(self):
        assert escape_bibtex("Test & Test") == r"Test \& Test"
        assert escape_bibtex("100%") == r"100\%"
        assert escape_bibtex("$5") == r"\$5"
        assert escape_bibtex("item_1") == r"item\_1"

    def test_generate_cite_key(self, sample_article):
        key = generate_cite_key(sample_article)

        assert "smith" in key
        assert "2023" in key

    def test_generate_cite_key_no_author(self):
        record = BibliographyRecord(
            id="test-123",
            title="Some Title",
        )
        key = generate_cite_key(record)

        # Should fall back to modified ID
        assert key

    def test_record_to_bibtex(self, sample_article):
        bibtex = record_to_bibtex(sample_article)

        assert "@article{" in bibtex
        assert "author = {Smith, John and Doe, Jane}" in bibtex
        assert "title = {{A Study of Something Important}}" in bibtex
        assert "year = {2023}" in bibtex
        assert "journal = {Journal of Testing}" in bibtex
        assert "volume = {10}" in bibtex
        assert "number = {2}" in bibtex
        assert "pages = {100--120}" in bibtex
        assert "doi = {10.1234/test.2023}" in bibtex

    def test_record_to_bibtex_book(self, sample_book):
        bibtex = record_to_bibtex(sample_book)

        assert "@book{" in bibtex
        assert "publisher = {Academic Press}" in bibtex
        assert "address = {New York}" in bibtex
        assert "isbn = {978-1234567890}" in bibtex

    def test_record_to_bibtex_custom_key(self, sample_article):
        bibtex = record_to_bibtex(sample_article, cite_key="custom_key")

        assert "@article{custom_key," in bibtex

    def test_records_to_bibtex(self, sample_article, sample_book):
        bibtex = records_to_bibtex([sample_article, sample_book])

        assert "@article{" in bibtex
        assert "@book{" in bibtex

    def test_export_bibtex_string(self, sample_article):
        bibtex = export_bibtex_string(sample_article)

        assert "@article{" in bibtex

    def test_export_bibtex_file(self, sample_article, tmp_path):
        output_file = tmp_path / "test.bib"
        export_bibtex(sample_article, output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "@article{" in content

    def test_bibtex_cyrillic(self, sample_russian):
        bibtex = export_bibtex_string(sample_russian)

        assert "Иванов" in bibtex
        assert "Исследование" in bibtex

    def test_bibtex_special_chars_in_title(self):
        record = BibliographyRecord(
            id="test",
            title="Study of X & Y: A 100% Complete Analysis",
            author=[Author(family="Test")],
            issued=DateParts(year=2020),
        )
        bibtex = record_to_bibtex(record)

        # Special chars should be escaped
        assert r"\&" in bibtex
        assert r"\%" in bibtex


class TestExportMultipleFormats:
    """Test exporting same record to multiple formats."""

    def test_all_formats(self, sample_article, tmp_path):
        # Export to all formats
        json_file = tmp_path / "test.json"
        ris_file = tmp_path / "test.ris"
        bib_file = tmp_path / "test.bib"

        export_csl_json(sample_article, json_file)
        export_ris(sample_article, ris_file)
        export_bibtex(sample_article, bib_file)

        # All files should exist
        assert json_file.exists()
        assert ris_file.exists()
        assert bib_file.exists()

        # All should contain the title
        assert "A Study of Something Important" in json_file.read_text()
        assert "A Study of Something Important" in ris_file.read_text()
        assert "A Study of Something Important" in bib_file.read_text()
