"""OCR extraction module using PaddleOCR."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from PIL import Image

from pdfhunter.models.evidence import BoundingBox


@dataclass
class OCRBlock:
    """A single OCR text block with metadata."""

    text: str
    bbox: BoundingBox
    confidence: float
    page_number: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "bbox": self.bbox.to_list(),
            "confidence": self.confidence,
            "page_number": self.page_number,
        }


@dataclass
class OCRResult:
    """Result of OCR processing for a page."""

    page_number: int
    blocks: list[OCRBlock] = field(default_factory=list)
    language_detected: str | None = None
    average_confidence: float = 0.0
    raw_text: str = ""

    def __post_init__(self):
        """Calculate derived fields."""
        if self.blocks:
            self.average_confidence = sum(b.confidence for b in self.blocks) / len(self.blocks)
            self.raw_text = "\n".join(b.text for b in self.blocks)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "page_number": self.page_number,
            "blocks": [b.to_dict() for b in self.blocks],
            "language_detected": self.language_detected,
            "average_confidence": self.average_confidence,
            "raw_text": self.raw_text,
        }

    def get_text(self) -> str:
        """Get concatenated text from all blocks."""
        return self.raw_text


class OCRExtractor:
    """OCR extractor using PaddleOCR."""

    def __init__(
        self,
        languages: list[str] | None = None,
        use_angle_cls: bool = True,
        use_gpu: bool = False,
    ):
        """Initialize OCR extractor.

        Args:
            languages: List of language codes (e.g., ['en', 'fr', 'ru'])
            use_angle_cls: Use angle classification for rotated text
            use_gpu: Use GPU acceleration
        """
        self.languages = languages or ["en"]
        self.use_angle_cls = use_angle_cls
        self.use_gpu = use_gpu
        self._ocr = None

    def _get_ocr(self):
        """Lazy initialization of PaddleOCR."""
        if self._ocr is None:
            from paddleocr import PaddleOCR
            import logging
            import os

            # Suppress PaddleOCR logging
            logging.getLogger("ppocr").setLevel(logging.WARNING)
            os.environ.setdefault("DISABLE_MODEL_SOURCE_CHECK", "True")

            # Map language codes to PaddleOCR format
            lang = self._map_language(self.languages[0] if self.languages else "en")

            # PaddleOCR API changed - only pass supported arguments
            self._ocr = PaddleOCR(
                use_textline_orientation=self.use_angle_cls,
                lang=lang,
            )
        return self._ocr

    def _map_language(self, lang: str) -> str:
        """Map language code to PaddleOCR language."""
        mapping = {
            "en": "en",
            "fr": "fr",
            "ru": "ru",
            "de": "german",
            "es": "es",
            "it": "it",
            "pt": "pt",
            "ch": "ch",
            "korean": "korean",
            "japan": "japan",
        }
        return mapping.get(lang.lower(), "en")

    def extract(
        self,
        image: Image.Image,
        page_number: int = 1,
        preprocess: bool = True,
    ) -> OCRResult:
        """Extract text from an image using OCR.

        Args:
            image: PIL Image to process
            page_number: Page number for reference
            preprocess: Apply preprocessing

        Returns:
            OCRResult with extracted text blocks
        """
        import numpy as np

        # Preprocess if requested
        if preprocess:
            from pdfhunter.extraction.preprocessor import create_default_preprocessor

            preprocessor = create_default_preprocessor()
            image = preprocessor.process(image)

        # Ensure image is RGB for PaddleOCR
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Convert to numpy array for PaddleOCR
        img_array = np.array(image)

        # Run OCR
        ocr = self._get_ocr()
        result = ocr.predict(img_array)

        # Parse results
        blocks = []
        if result and result[0]:
            for line in result[0]:
                bbox_points, (text, confidence) = line

                # Convert bbox points to BoundingBox
                # PaddleOCR returns [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                x_coords = [p[0] for p in bbox_points]
                y_coords = [p[1] for p in bbox_points]

                bbox = BoundingBox(
                    x1=min(x_coords),
                    y1=min(y_coords),
                    x2=max(x_coords),
                    y2=max(y_coords),
                )

                blocks.append(
                    OCRBlock(
                        text=text,
                        bbox=bbox,
                        confidence=float(confidence),
                        page_number=page_number,
                    )
                )

        # Detect language from content
        language_detected = self._detect_language("\n".join(b.text for b in blocks))

        return OCRResult(
            page_number=page_number,
            blocks=blocks,
            language_detected=language_detected,
        )

    def extract_from_file(
        self,
        image_path: str | Path,
        page_number: int = 1,
        preprocess: bool = True,
    ) -> OCRResult:
        """Extract text from an image file.

        Args:
            image_path: Path to image file
            page_number: Page number for reference
            preprocess: Apply preprocessing

        Returns:
            OCRResult with extracted text blocks
        """
        image = Image.open(image_path)
        return self.extract(image, page_number, preprocess)

    def _detect_language(self, text: str) -> str | None:
        """Detect language from text content.

        Simple heuristic based on character ranges.
        """
        if not text:
            return None

        # Count character types
        cyrillic_count = sum(1 for c in text if "\u0400" <= c <= "\u04ff")
        latin_count = sum(1 for c in text if "a" <= c.lower() <= "z")
        accent_count = sum(1 for c in text if c in "àâäéèêëïîôùûüÿçœæ")

        total = cyrillic_count + latin_count

        if total == 0:
            return None

        # Determine language
        if cyrillic_count / total > 0.3:
            return "ru"
        elif accent_count > 5:
            return "fr"
        else:
            return "en"


class TesseractExtractor:
    """Fallback OCR extractor using Tesseract."""

    def __init__(
        self,
        languages: list[str] | None = None,
        config: str = "",
    ):
        """Initialize Tesseract extractor.

        Args:
            languages: List of language codes
            config: Additional Tesseract config
        """
        self.languages = languages or ["eng"]
        self.config = config

    def _get_lang_string(self) -> str:
        """Get Tesseract language string."""
        mapping = {
            "en": "eng",
            "fr": "fra",
            "ru": "rus",
            "de": "deu",
            "es": "spa",
        }
        langs = [mapping.get(lang, lang) for lang in self.languages]
        return "+".join(langs)

    def extract(
        self,
        image: Image.Image,
        page_number: int = 1,
        preprocess: bool = True,
    ) -> OCRResult:
        """Extract text from an image using Tesseract.

        Args:
            image: PIL Image to process
            page_number: Page number for reference
            preprocess: Apply preprocessing

        Returns:
            OCRResult with extracted text blocks
        """
        import pytesseract

        # Preprocess if requested
        if preprocess:
            from pdfhunter.extraction.preprocessor import create_default_preprocessor

            preprocessor = create_default_preprocessor()
            image = preprocessor.process(image)

        # Get detailed data
        lang = self._get_lang_string()
        data = pytesseract.image_to_data(
            image, lang=lang, config=self.config, output_type=pytesseract.Output.DICT
        )

        # Parse results
        blocks = []
        n_boxes = len(data["text"])

        for i in range(n_boxes):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])

            # Skip empty or low confidence
            if not text or conf < 0:
                continue

            bbox = BoundingBox(
                x1=float(data["left"][i]),
                y1=float(data["top"][i]),
                x2=float(data["left"][i] + data["width"][i]),
                y2=float(data["top"][i] + data["height"][i]),
            )

            blocks.append(
                OCRBlock(
                    text=text,
                    bbox=bbox,
                    confidence=conf / 100.0,
                    page_number=page_number,
                )
            )

        return OCRResult(
            page_number=page_number,
            blocks=blocks,
        )


def create_ocr_extractor(
    engine: Literal["paddleocr", "tesseract"] = "paddleocr",
    languages: list[str] | None = None,
    use_gpu: bool = False,
) -> OCRExtractor | TesseractExtractor:
    """Factory function to create an OCR extractor.

    Args:
        engine: OCR engine to use
        languages: List of language codes
        use_gpu: Use GPU acceleration (PaddleOCR only)

    Returns:
        OCR extractor instance
    """
    if engine == "paddleocr":
        return OCRExtractor(languages=languages, use_gpu=use_gpu)
    elif engine == "tesseract":
        return TesseractExtractor(languages=languages)
    else:
        raise ValueError(f"Unknown OCR engine: {engine}")
