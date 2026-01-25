"""Text extraction from PDF documents with text layers."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pdfplumber

from pdfhunter.models.evidence import BoundingBox


@dataclass
class TextBlock:
    """A single text block extracted from PDF."""

    text: str
    bbox: BoundingBox | None = None
    page_number: int = 1
    font_name: str | None = None
    font_size: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "text": self.text,
            "page_number": self.page_number,
        }
        if self.bbox:
            result["bbox"] = self.bbox.to_list()
        if self.font_name:
            result["font_name"] = self.font_name
        if self.font_size:
            result["font_size"] = self.font_size
        return result


@dataclass
class TextExtractionResult:
    """Result of text extraction for a page."""

    page_number: int
    blocks: list[TextBlock] = field(default_factory=list)
    raw_text: str = ""
    word_count: int = 0
    char_count: int = 0

    def __post_init__(self):
        """Calculate derived fields."""
        if not self.raw_text and self.blocks:
            self.raw_text = "\n".join(b.text for b in self.blocks)
        if self.raw_text:
            self.char_count = len(self.raw_text)
            self.word_count = len(self.raw_text.split())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "page_number": self.page_number,
            "blocks": [b.to_dict() for b in self.blocks],
            "raw_text": self.raw_text,
            "word_count": self.word_count,
            "char_count": self.char_count,
        }

    def get_text(self) -> str:
        """Get the raw text content."""
        return self.raw_text

    def is_empty(self) -> bool:
        """Check if extraction result is empty."""
        return self.char_count < 10


class TextExtractor:
    """Text extractor for PDFs with text layers."""

    def __init__(
        self,
        extract_words: bool = True,
        extract_lines: bool = False,
        keep_blank_chars: bool = False,
    ):
        """Initialize text extractor.

        Args:
            extract_words: Extract individual words with bounding boxes
            extract_lines: Extract text line by line
            keep_blank_chars: Keep blank characters in output
        """
        self.extract_words = extract_words
        self.extract_lines = extract_lines
        self.keep_blank_chars = keep_blank_chars

    def extract_page(
        self,
        pdf_path: str | Path,
        page_number: int,
    ) -> TextExtractionResult:
        """Extract text from a single page.

        Args:
            pdf_path: Path to PDF file
            page_number: 1-indexed page number

        Returns:
            TextExtractionResult with extracted text
        """
        pdf_path = Path(pdf_path)

        with pdfplumber.open(pdf_path) as pdf:
            if page_number < 1 or page_number > len(pdf.pages):
                raise ValueError(
                    f"Invalid page number {page_number}. PDF has {len(pdf.pages)} pages."
                )

            page = pdf.pages[page_number - 1]
            return self._extract_from_page(page, page_number)

    def extract_pages(
        self,
        pdf_path: str | Path,
        page_numbers: list[int] | None = None,
    ) -> list[TextExtractionResult]:
        """Extract text from multiple pages.

        Args:
            pdf_path: Path to PDF file
            page_numbers: List of 1-indexed page numbers (None = all pages)

        Returns:
            List of TextExtractionResult
        """
        pdf_path = Path(pdf_path)
        results = []

        with pdfplumber.open(pdf_path) as pdf:
            if page_numbers is None:
                page_numbers = list(range(1, len(pdf.pages) + 1))

            for page_num in page_numbers:
                if page_num < 1 or page_num > len(pdf.pages):
                    continue
                page = pdf.pages[page_num - 1]
                result = self._extract_from_page(page, page_num)
                results.append(result)

        return results

    def _extract_from_page(
        self,
        page: pdfplumber.page.Page,
        page_number: int,
    ) -> TextExtractionResult:
        """Extract text from a pdfplumber page object.

        Args:
            page: pdfplumber Page object
            page_number: Page number for reference

        Returns:
            TextExtractionResult
        """
        blocks: list[TextBlock] = []

        # Extract full text
        raw_text = page.extract_text(
            keep_blank_chars=self.keep_blank_chars,
        ) or ""

        # Extract words with bounding boxes if requested
        if self.extract_words:
            words = page.extract_words(
                keep_blank_chars=self.keep_blank_chars,
                extra_attrs=["fontname", "size"],
            )

            for word in words:
                bbox = BoundingBox(
                    x1=float(word["x0"]),
                    y1=float(word["top"]),
                    x2=float(word["x1"]),
                    y2=float(word["bottom"]),
                )

                blocks.append(
                    TextBlock(
                        text=word["text"],
                        bbox=bbox,
                        page_number=page_number,
                        font_name=word.get("fontname"),
                        font_size=word.get("size"),
                    )
                )

        # Extract lines if requested
        elif self.extract_lines:
            lines = raw_text.split("\n")
            for line in lines:
                if line.strip():
                    blocks.append(
                        TextBlock(
                            text=line.strip(),
                            page_number=page_number,
                        )
                    )

        return TextExtractionResult(
            page_number=page_number,
            blocks=blocks,
            raw_text=raw_text,
        )

    def extract_text_simple(
        self,
        pdf_path: str | Path,
        page_numbers: list[int] | None = None,
    ) -> str:
        """Simple text extraction without detailed metadata.

        Args:
            pdf_path: Path to PDF file
            page_numbers: List of 1-indexed page numbers (None = all pages)

        Returns:
            Concatenated text from all pages
        """
        results = self.extract_pages(pdf_path, page_numbers)
        return "\n\n".join(r.raw_text for r in results if r.raw_text)


class TextRegionExtractor:
    """Extract text from specific regions of a page."""

    def __init__(self):
        """Initialize region extractor."""
        pass

    def extract_header(
        self,
        pdf_path: str | Path,
        page_number: int,
        header_ratio: float = 0.15,
    ) -> TextExtractionResult:
        """Extract text from page header region.

        Args:
            pdf_path: Path to PDF file
            page_number: 1-indexed page number
            header_ratio: Portion of page height to consider as header

        Returns:
            TextExtractionResult from header region
        """
        return self._extract_region(
            pdf_path, page_number, top_ratio=0, bottom_ratio=header_ratio
        )

    def extract_footer(
        self,
        pdf_path: str | Path,
        page_number: int,
        footer_ratio: float = 0.15,
    ) -> TextExtractionResult:
        """Extract text from page footer region.

        Args:
            pdf_path: Path to PDF file
            page_number: 1-indexed page number
            footer_ratio: Portion of page height to consider as footer

        Returns:
            TextExtractionResult from footer region
        """
        return self._extract_region(
            pdf_path, page_number, top_ratio=1 - footer_ratio, bottom_ratio=1
        )

    def extract_running_header(
        self,
        pdf_path: str | Path,
        page_numbers: list[int],
    ) -> list[str]:
        """Extract running headers from multiple pages.

        Useful for finding journal name, volume, page numbers.

        Args:
            pdf_path: Path to PDF file
            page_numbers: Pages to check

        Returns:
            List of header texts
        """
        headers = []
        for page_num in page_numbers:
            try:
                result = self.extract_header(pdf_path, page_num, header_ratio=0.1)
                if result.raw_text.strip():
                    headers.append(result.raw_text.strip())
            except Exception:
                continue
        return headers

    def _extract_region(
        self,
        pdf_path: str | Path,
        page_number: int,
        top_ratio: float,
        bottom_ratio: float,
        left_ratio: float = 0,
        right_ratio: float = 1,
    ) -> TextExtractionResult:
        """Extract text from a specific region of the page.

        Args:
            pdf_path: Path to PDF file
            page_number: 1-indexed page number
            top_ratio: Top boundary as ratio of page height (0-1)
            bottom_ratio: Bottom boundary as ratio of page height (0-1)
            left_ratio: Left boundary as ratio of page width (0-1)
            right_ratio: Right boundary as ratio of page width (0-1)

        Returns:
            TextExtractionResult from the specified region
        """
        pdf_path = Path(pdf_path)

        with pdfplumber.open(pdf_path) as pdf:
            if page_number < 1 or page_number > len(pdf.pages):
                raise ValueError(f"Invalid page number {page_number}")

            page = pdf.pages[page_number - 1]

            # Calculate crop boundaries
            width = page.width
            height = page.height

            bbox = (
                left_ratio * width,
                top_ratio * height,
                right_ratio * width,
                bottom_ratio * height,
            )

            # Crop and extract
            cropped = page.crop(bbox)
            text = cropped.extract_text() or ""

            # Extract words from cropped region
            blocks = []
            words = cropped.extract_words()
            for word in words:
                word_bbox = BoundingBox(
                    x1=float(word["x0"]) + bbox[0],
                    y1=float(word["top"]) + bbox[1],
                    x2=float(word["x1"]) + bbox[0],
                    y2=float(word["bottom"]) + bbox[1],
                )
                blocks.append(
                    TextBlock(
                        text=word["text"],
                        bbox=word_bbox,
                        page_number=page_number,
                    )
                )

            return TextExtractionResult(
                page_number=page_number,
                blocks=blocks,
                raw_text=text,
            )


def create_text_extractor(
    extract_words: bool = True,
    extract_lines: bool = False,
) -> TextExtractor:
    """Factory function to create a text extractor.

    Args:
        extract_words: Extract individual words with bounding boxes
        extract_lines: Extract text line by line

    Returns:
        TextExtractor instance
    """
    return TextExtractor(
        extract_words=extract_words,
        extract_lines=extract_lines,
    )
