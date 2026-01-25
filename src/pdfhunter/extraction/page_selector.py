"""Page selection strategies for bibliographic extraction."""

from dataclasses import dataclass
from enum import Enum

from pdfhunter.core.document import Document, DocumentType


class PageRole(str, Enum):
    """Role of a page in bibliographic extraction."""

    TITLE = "title"  # Title page (usually p1)
    TITLE_VERSO = "title_verso"  # Back of title page (p2)
    BODY_START = "body_start"  # First body page (p3)
    COLOPHON = "colophon"  # Publication info (usually last or last-1)
    TOC = "toc"  # Table of contents
    RUNNING_HEADER = "running_header"  # Page with running header


@dataclass
class SelectedPage:
    """A page selected for processing."""

    page_number: int
    role: PageRole
    priority: int  # Lower = higher priority


class PageSelector:
    """Selects pages for bibliographic extraction."""

    def __init__(self, document: Document):
        self.document = document
        self.page_count = document.page_count

    def select_default_pages(self) -> list[SelectedPage]:
        """Select default pages based on document type.

        For scanned PDFs: p1, p2, last
        For text PDFs: p1, p2, p3, last
        For images: p1 only
        """
        if self.document.document_type == DocumentType.IMAGE:
            return [SelectedPage(page_number=1, role=PageRole.TITLE, priority=1)]

        pages: list[SelectedPage] = []

        # Always include first page (title)
        pages.append(SelectedPage(page_number=1, role=PageRole.TITLE, priority=1))

        # Include second page if exists (title verso)
        if self.page_count >= 2:
            pages.append(SelectedPage(page_number=2, role=PageRole.TITLE_VERSO, priority=2))

        # For text PDFs, also include third page
        if self.document.document_type == DocumentType.TEXT_PDF and self.page_count >= 3:
            pages.append(SelectedPage(page_number=3, role=PageRole.BODY_START, priority=3))

        # Include last page if different from already selected
        if self.page_count >= 3:
            last_page = self.page_count
            if last_page not in [p.page_number for p in pages]:
                pages.append(
                    SelectedPage(page_number=last_page, role=PageRole.COLOPHON, priority=4)
                )

        return sorted(pages, key=lambda p: p.priority)

    def select_expansion_pages(
        self, missing_fields: list[str], already_processed: set[int]
    ) -> list[SelectedPage]:
        """Select additional pages based on missing fields.

        Args:
            missing_fields: List of field names that are missing
            already_processed: Set of page numbers already processed

        Returns:
            List of additional pages to process
        """
        pages: list[SelectedPage] = []

        # pages/volume missing → try running headers (middle pages)
        if "page" in missing_fields or "volume" in missing_fields:
            middle_pages = self._get_middle_pages(already_processed)
            for i, pg in enumerate(middle_pages[:3]):  # Max 3 middle pages
                pages.append(
                    SelectedPage(page_number=pg, role=PageRole.RUNNING_HEADER, priority=10 + i)
                )

        # publisher/place missing → try last-1
        if "publisher" in missing_fields or "publisher_place" in missing_fields:
            if self.page_count >= 4:
                last_minus_one = self.page_count - 1
                if last_minus_one not in already_processed:
                    pages.append(
                        SelectedPage(
                            page_number=last_minus_one, role=PageRole.COLOPHON, priority=5
                        )
                    )

        # container_title missing → try TOC (pages 3-5)
        if "container_title" in missing_fields:
            for pg in range(3, min(6, self.page_count + 1)):
                if pg not in already_processed:
                    pages.append(SelectedPage(page_number=pg, role=PageRole.TOC, priority=6))
                    break

        return pages

    def _get_middle_pages(self, exclude: set[int]) -> list[int]:
        """Get middle pages for running header search."""
        if self.page_count <= 4:
            return []

        # Sample evenly from middle section
        start = 3
        end = self.page_count - 1
        middle_range = list(range(start, end + 1))

        # Filter out already processed
        available = [p for p in middle_range if p not in exclude]

        # Sample up to 5 pages evenly
        if len(available) <= 5:
            return available

        step = len(available) // 5
        return [available[i * step] for i in range(5)]

    def get_page_numbers(self) -> list[int]:
        """Get list of page numbers to process (convenience method)."""
        return [p.page_number for p in self.select_default_pages()]
