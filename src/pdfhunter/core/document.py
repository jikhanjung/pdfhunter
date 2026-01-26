"""Document class for handling PDF and image files."""

from enum import Enum
from pathlib import Path
from typing import Any

from PIL import Image
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Type of document based on content."""

    TEXT_PDF = "text_pdf"  # PDF with text layer
    SCANNED_PDF = "scanned_pdf"  # PDF without text layer (needs OCR)
    IMAGE = "image"  # Single image file


class PageInfo(BaseModel):
    """Information about a single page."""

    page_number: int
    width: float
    height: float
    has_text: bool = False
    text_length: int = 0


class DocumentMetadata(BaseModel):
    """Metadata extracted from the document."""

    filename: str
    file_path: Path
    document_type: DocumentType
    page_count: int
    pages: list[PageInfo] = Field(default_factory=list)
    has_text_layer: bool = False
    file_size_bytes: int = 0

    # PDF metadata fields
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    keywords: str | None = None
    creator: str | None = None  # Application that created the document
    producer: str | None = None  # PDF producer
    creation_date: str | None = None
    modification_date: str | None = None

    def has_useful_metadata(self) -> bool:
        """Check if PDF has useful bibliographic metadata."""
        return bool(self.title or self.author or self.subject)

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary for debugging."""
        return {
            "title": self.title,
            "author": self.author,
            "subject": self.subject,
            "keywords": self.keywords,
            "creator": self.creator,
            "creation_date": self.creation_date,
        }


class Document:
    """Wrapper for PDF and image documents."""

    SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}
    SUPPORTED_PDF_EXTENSIONS = {".pdf"}

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        self._metadata: DocumentMetadata | None = None
        self._pdf_doc: Any = None
        self._image: Image.Image | None = None

    @property
    def metadata(self) -> DocumentMetadata:
        """Get document metadata, loading if necessary."""
        if self._metadata is None:
            self._metadata = self._load_metadata()
        return self._metadata

    @property
    def is_pdf(self) -> bool:
        """Check if document is a PDF."""
        return self.file_path.suffix.lower() in self.SUPPORTED_PDF_EXTENSIONS

    @property
    def is_image(self) -> bool:
        """Check if document is an image."""
        return self.file_path.suffix.lower() in self.SUPPORTED_IMAGE_EXTENSIONS

    @property
    def document_type(self) -> DocumentType:
        """Get the document type."""
        return self.metadata.document_type

    @property
    def page_count(self) -> int:
        """Get the number of pages."""
        return self.metadata.page_count

    def _load_metadata(self) -> DocumentMetadata:
        """Load metadata from the document."""
        if self.is_pdf:
            return self._load_pdf_metadata()
        elif self.is_image:
            return self._load_image_metadata()
        else:
            raise ValueError(f"Unsupported file type: {self.file_path.suffix}")

    def _load_pdf_metadata(self) -> DocumentMetadata:
        """Load metadata from a PDF file."""
        import pdfplumber
        from pypdf import PdfReader

        file_size = self.file_path.stat().st_size

        # Use pypdf for basic metadata
        reader = PdfReader(self.file_path)
        pdf_metadata = reader.metadata or {}

        # Use pdfplumber for detailed page info
        pages: list[PageInfo] = []
        total_text_length = 0

        with pdfplumber.open(self.file_path) as pdf:
            self._pdf_doc = pdf
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                text_length = len(text.strip())
                total_text_length += text_length

                pages.append(
                    PageInfo(
                        page_number=i + 1,
                        width=float(page.width),
                        height=float(page.height),
                        has_text=text_length > 50,  # Threshold for "has text"
                        text_length=text_length,
                    )
                )

        # Determine if PDF has meaningful text layer
        # Consider it a text PDF if average text per page > 100 chars
        has_text_layer = (total_text_length / len(pages)) > 100 if pages else False

        # Extract all available PDF metadata
        def clean_metadata(value: Any) -> str | None:
            """Clean metadata value, removing empty strings."""
            if value is None:
                return None
            s = str(value).strip()
            return s if s else None

        return DocumentMetadata(
            filename=self.file_path.name,
            file_path=self.file_path,
            document_type=DocumentType.TEXT_PDF if has_text_layer else DocumentType.SCANNED_PDF,
            page_count=len(pages),
            pages=pages,
            has_text_layer=has_text_layer,
            file_size_bytes=file_size,
            # PDF metadata fields
            title=clean_metadata(pdf_metadata.get("/Title")),
            author=clean_metadata(pdf_metadata.get("/Author")),
            subject=clean_metadata(pdf_metadata.get("/Subject")),
            keywords=clean_metadata(pdf_metadata.get("/Keywords")),
            creator=clean_metadata(pdf_metadata.get("/Creator")),
            producer=clean_metadata(pdf_metadata.get("/Producer")),
            creation_date=clean_metadata(pdf_metadata.get("/CreationDate")),
            modification_date=clean_metadata(pdf_metadata.get("/ModDate")),
        )

    def _load_image_metadata(self) -> DocumentMetadata:
        """Load metadata from an image file."""
        file_size = self.file_path.stat().st_size

        with Image.open(self.file_path) as img:
            width, height = img.size

        return DocumentMetadata(
            filename=self.file_path.name,
            file_path=self.file_path,
            document_type=DocumentType.IMAGE,
            page_count=1,
            pages=[
                PageInfo(
                    page_number=1,
                    width=float(width),
                    height=float(height),
                    has_text=False,
                    text_length=0,
                )
            ],
            has_text_layer=False,
            file_size_bytes=file_size,
        )

    def render_page(self, page_number: int, dpi: int = 200) -> Image.Image:
        """Render a page as an image.

        Args:
            page_number: 1-indexed page number
            dpi: Resolution for rendering (default 200)

        Returns:
            PIL Image object
        """
        if self.is_image:
            if page_number != 1:
                raise ValueError("Image documents only have 1 page")
            return Image.open(self.file_path)

        if self.is_pdf:
            from pdf2image import convert_from_path

            # Convert only the requested page
            images = convert_from_path(
                self.file_path,
                first_page=page_number,
                last_page=page_number,
                dpi=dpi,
            )
            if not images:
                raise ValueError(f"Failed to render page {page_number}")
            return images[0]

        raise ValueError(f"Cannot render page for document type: {self.document_type}")

    def extract_text(self, page_number: int) -> str:
        """Extract text from a page (for text PDFs only).

        Args:
            page_number: 1-indexed page number

        Returns:
            Extracted text string
        """
        if not self.is_pdf:
            raise ValueError("Text extraction only supported for PDFs")

        if self.document_type == DocumentType.SCANNED_PDF:
            raise ValueError("Use OCR for scanned PDFs")

        import pdfplumber

        with pdfplumber.open(self.file_path) as pdf:
            if page_number < 1 or page_number > len(pdf.pages):
                raise ValueError(f"Invalid page number: {page_number}")
            page = pdf.pages[page_number - 1]
            return page.extract_text() or ""

    def get_page_indices(self, strategy: str = "default") -> list[int]:
        """Get page indices to process based on strategy.

        Args:
            strategy: 'default' for standard pages, 'text' for text PDFs

        Returns:
            List of 1-indexed page numbers
        """
        total = self.page_count

        if total == 0:
            return []

        if strategy == "text" or self.document_type == DocumentType.TEXT_PDF:
            # Text PDF: p1, p2, p3, last
            pages = [1]
            if total >= 2:
                pages.append(2)
            if total >= 3:
                pages.append(3)
            if total >= 4:
                pages.append(total)
            return sorted(set(pages))
        else:
            # Scanned PDF: p1, p2, last
            pages = [1]
            if total >= 2:
                pages.append(2)
            if total >= 3:
                pages.append(total)
            return sorted(set(pages))

    def __repr__(self) -> str:
        return f"Document({self.file_path.name}, type={self.document_type.value}, pages={self.page_count})"
