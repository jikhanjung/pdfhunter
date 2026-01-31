"""Tests for text extractor module."""

import pytest

from pdfresolve.extraction.text_extractor import (
    TextBlock,
    TextExtractionResult,
    TextExtractor,
    TextRegionExtractor,
    create_text_extractor,
)
from pdfresolve.models.evidence import BoundingBox


class TestTextBlock:
    def test_create_block(self):
        block = TextBlock(
            text="Test text",
            page_number=1,
        )
        assert block.text == "Test text"
        assert block.page_number == 1
        assert block.bbox is None

    def test_block_with_bbox(self):
        bbox = BoundingBox(x1=10, y1=20, x2=100, y2=40)
        block = TextBlock(
            text="Test",
            bbox=bbox,
            page_number=2,
            font_name="Arial",
            font_size=12.0,
        )
        assert block.bbox == bbox
        assert block.font_name == "Arial"
        assert block.font_size == 12.0

    def test_block_to_dict(self):
        bbox = BoundingBox(x1=10, y1=20, x2=100, y2=40)
        block = TextBlock(
            text="Test",
            bbox=bbox,
            page_number=1,
            font_name="Times",
            font_size=11.0,
        )
        d = block.to_dict()

        assert d["text"] == "Test"
        assert d["page_number"] == 1
        assert d["bbox"] == [10, 20, 100, 40]
        assert d["font_name"] == "Times"
        assert d["font_size"] == 11.0

    def test_block_to_dict_minimal(self):
        block = TextBlock(text="Minimal", page_number=3)
        d = block.to_dict()

        assert d["text"] == "Minimal"
        assert d["page_number"] == 3
        assert "bbox" not in d
        assert "font_name" not in d


class TestTextExtractionResult:
    def test_empty_result(self):
        result = TextExtractionResult(page_number=1)
        assert result.page_number == 1
        assert result.blocks == []
        assert result.raw_text == ""
        assert result.word_count == 0
        assert result.char_count == 0
        assert result.is_empty()

    def test_result_with_raw_text(self):
        result = TextExtractionResult(
            page_number=1,
            raw_text="Hello world test",
        )
        assert result.word_count == 3
        assert result.char_count == 16
        assert not result.is_empty()

    def test_result_with_blocks(self):
        blocks = [
            TextBlock(text="Line 1", page_number=1),
            TextBlock(text="Line 2", page_number=1),
        ]
        result = TextExtractionResult(page_number=1, blocks=blocks)

        assert "Line 1" in result.raw_text
        assert "Line 2" in result.raw_text
        assert result.word_count == 4

    def test_result_to_dict(self):
        result = TextExtractionResult(
            page_number=2,
            raw_text="Test content",
        )
        d = result.to_dict()

        assert d["page_number"] == 2
        assert d["raw_text"] == "Test content"
        assert d["word_count"] == 2
        assert d["char_count"] == 12

    def test_get_text(self):
        result = TextExtractionResult(
            page_number=1,
            raw_text="Sample text here",
        )
        assert result.get_text() == "Sample text here"

    def test_is_empty_threshold(self):
        # Less than 10 chars is considered empty
        result1 = TextExtractionResult(page_number=1, raw_text="short")
        assert result1.is_empty()

        result2 = TextExtractionResult(page_number=1, raw_text="long enough text")
        assert not result2.is_empty()


class TestTextExtractor:
    def test_create_extractor(self):
        extractor = TextExtractor()
        assert extractor.extract_words is True
        assert extractor.extract_lines is False

    def test_create_extractor_with_options(self):
        extractor = TextExtractor(
            extract_words=False,
            extract_lines=True,
            keep_blank_chars=True,
        )
        assert extractor.extract_words is False
        assert extractor.extract_lines is True
        assert extractor.keep_blank_chars is True


class TestTextRegionExtractor:
    def test_create_region_extractor(self):
        extractor = TextRegionExtractor()
        assert extractor is not None


class TestTextExtractorFactory:
    def test_create_default(self):
        extractor = create_text_extractor()
        assert isinstance(extractor, TextExtractor)
        assert extractor.extract_words is True

    def test_create_line_mode(self):
        extractor = create_text_extractor(extract_words=False, extract_lines=True)
        assert extractor.extract_words is False
        assert extractor.extract_lines is True


# Integration tests - require actual PDF files
@pytest.mark.integration
class TestTextExtractorIntegration:
    """Integration tests that require PDF files."""

    def test_extract_from_pdf(self, tmp_path):
        """Test extraction from a real PDF."""
        # This test would require a sample PDF file
        # For now, it's a placeholder
        pass

    def test_extract_header_region(self, tmp_path):
        """Test header region extraction."""
        pass

    def test_extract_running_headers(self, tmp_path):
        """Test running header extraction from multiple pages."""
        pass
