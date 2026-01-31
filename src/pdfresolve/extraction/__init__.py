"""Extraction modules for text and OCR processing."""

from pdfresolve.extraction.ocr_extractor import (
    OCRBlock,
    OCRExtractor,
    OCRResult,
    TesseractExtractor,
    create_ocr_extractor,
)
from pdfresolve.extraction.page_selector import PageRole, PageSelector, SelectedPage
from pdfresolve.extraction.preprocessor import ImagePreprocessor, create_default_preprocessor
from pdfresolve.extraction.text_extractor import (
    TextBlock,
    TextExtractionResult,
    TextExtractor,
    TextRegionExtractor,
    create_text_extractor,
)

__all__ = [
    # OCR
    "OCRBlock",
    "OCRExtractor",
    "OCRResult",
    "TesseractExtractor",
    "create_ocr_extractor",
    # Page selection
    "PageRole",
    "PageSelector",
    "SelectedPage",
    # Preprocessing
    "ImagePreprocessor",
    "create_default_preprocessor",
    # Text extraction
    "TextBlock",
    "TextExtractionResult",
    "TextExtractor",
    "TextRegionExtractor",
    "create_text_extractor",
]
