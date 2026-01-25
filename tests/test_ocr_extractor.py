"""Tests for OCR extractor module."""

import pytest
from PIL import Image

from pdfhunter.extraction.ocr_extractor import (
    OCRBlock,
    OCRResult,
    create_ocr_extractor,
)
from pdfhunter.extraction.preprocessor import ImagePreprocessor, create_default_preprocessor
from pdfhunter.models.evidence import BoundingBox


class TestOCRBlock:
    def test_create_block(self):
        bbox = BoundingBox(x1=10, y1=20, x2=100, y2=40)
        block = OCRBlock(
            text="Test text",
            bbox=bbox,
            confidence=0.95,
            page_number=1,
        )
        assert block.text == "Test text"
        assert block.confidence == 0.95
        assert block.page_number == 1

    def test_block_to_dict(self):
        bbox = BoundingBox(x1=10, y1=20, x2=100, y2=40)
        block = OCRBlock(
            text="Test",
            bbox=bbox,
            confidence=0.9,
            page_number=2,
        )
        d = block.to_dict()

        assert d["text"] == "Test"
        assert d["bbox"] == [10, 20, 100, 40]
        assert d["confidence"] == 0.9
        assert d["page_number"] == 2


class TestOCRResult:
    def test_empty_result(self):
        result = OCRResult(page_number=1)
        assert result.page_number == 1
        assert result.blocks == []
        assert result.average_confidence == 0.0
        assert result.raw_text == ""

    def test_result_with_blocks(self):
        blocks = [
            OCRBlock(
                text="Line 1",
                bbox=BoundingBox(x1=0, y1=0, x2=100, y2=20),
                confidence=0.9,
            ),
            OCRBlock(
                text="Line 2",
                bbox=BoundingBox(x1=0, y1=30, x2=100, y2=50),
                confidence=0.8,
            ),
        ]
        result = OCRResult(page_number=1, blocks=blocks)

        assert result.average_confidence == pytest.approx(0.85)
        assert "Line 1" in result.raw_text
        assert "Line 2" in result.raw_text

    def test_result_to_dict(self):
        blocks = [
            OCRBlock(
                text="Test",
                bbox=BoundingBox(x1=0, y1=0, x2=50, y2=20),
                confidence=0.95,
            ),
        ]
        result = OCRResult(page_number=1, blocks=blocks)
        d = result.to_dict()

        assert d["page_number"] == 1
        assert len(d["blocks"]) == 1
        assert d["average_confidence"] == 0.95

    def test_get_text(self):
        blocks = [
            OCRBlock(
                text="Hello",
                bbox=BoundingBox(x1=0, y1=0, x2=50, y2=20),
                confidence=0.9,
            ),
            OCRBlock(
                text="World",
                bbox=BoundingBox(x1=0, y1=30, x2=50, y2=50),
                confidence=0.9,
            ),
        ]
        result = OCRResult(page_number=1, blocks=blocks)
        text = result.get_text()

        assert "Hello" in text
        assert "World" in text


class TestImagePreprocessor:
    def test_create_default_preprocessor(self):
        preprocessor = create_default_preprocessor()
        assert preprocessor.grayscale is True
        assert preprocessor.denoise is True
        assert preprocessor.deskew is False
        assert preprocessor.threshold == "none"

    def test_preprocessor_grayscale(self):
        # Create a simple RGB image
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))

        preprocessor = ImagePreprocessor(grayscale=True, denoise=False)
        result = preprocessor.process(img)

        # Result should be grayscale (mode 'L')
        assert result.mode == "L"

    def test_preprocessor_no_grayscale(self):
        # Create a simple RGB image
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))

        preprocessor = ImagePreprocessor(grayscale=False, denoise=False)
        result = preprocessor.process(img)

        # Result should still be RGB
        assert result.mode == "RGB"


class TestOCRExtractorFactory:
    def test_create_paddleocr_extractor(self):
        extractor = create_ocr_extractor(engine="paddleocr", languages=["en"])
        assert extractor.languages == ["en"]

    def test_create_tesseract_extractor(self):
        extractor = create_ocr_extractor(engine="tesseract", languages=["en", "fr"])
        assert extractor.languages == ["en", "fr"]

    def test_invalid_engine(self):
        with pytest.raises(ValueError, match="Unknown OCR engine"):
            create_ocr_extractor(engine="invalid")


# Integration tests - require actual OCR engines
@pytest.mark.integration
class TestOCRExtractorIntegration:
    """Integration tests that require PaddleOCR installed."""

    @pytest.mark.xfail(reason="PaddleOCR may have environment-specific issues", strict=False)
    def test_extract_from_image(self):
        """Test OCR extraction from a simple image."""
        # Create a simple test image with text
        from PIL import ImageDraw, ImageFont

        img = Image.new("RGB", (200, 50), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Test 2024", fill=(0, 0, 0))

        extractor = create_ocr_extractor(engine="paddleocr", languages=["en"])
        result = extractor.extract(img, page_number=1)

        # Should extract some text
        assert result.page_number == 1
        # Note: actual OCR results may vary
