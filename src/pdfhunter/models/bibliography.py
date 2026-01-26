"""Bibliography data models following CSL-JSON schema."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from pdfhunter.models.evidence import Evidence


class RecordStatus(str, Enum):
    """Status of a bibliography record."""

    CONFIRMED = "confirmed"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class Author(BaseModel):
    """Author information."""

    family: str | None = None
    given: str | None = None
    literal: str | None = None  # For names that shouldn't be parsed

    def to_csl(self) -> dict[str, str]:
        """Convert to CSL-JSON author format."""
        if self.literal:
            return {"literal": self.literal}
        result = {}
        if self.family:
            result["family"] = self.family
        if self.given:
            result["given"] = self.given
        return result


class DateParts(BaseModel):
    """Date information."""

    year: int | None = None
    month: int | None = None
    day: int | None = None

    def to_csl(self) -> dict[str, list[list[int]]]:
        """Convert to CSL-JSON date-parts format."""
        parts = []
        if self.year:
            parts.append(self.year)
            if self.month:
                parts.append(self.month)
                if self.day:
                    parts.append(self.day)
        if parts:
            return {"date-parts": [parts]}
        return {}


class BibliographyRecord(BaseModel):
    """Bibliography record following CSL-JSON structure."""

    # Required fields
    id: str
    type: str = "article"  # article, book, chapter, report, etc.

    # Core fields
    title: str | None = None
    author: list[Author] = Field(default_factory=list)
    issued: DateParts | None = None

    # Container fields (for articles in journals/books)
    container_title: str | None = None  # Journal or book title
    volume: str | None = None
    issue: str | None = None
    page: str | None = None  # e.g., "123-456"

    # Publication fields
    publisher: str | None = None
    publisher_place: str | None = None

    # Series fields
    collection_title: str | None = None  # Series name
    collection_number: str | None = None  # Series number

    # Identifiers
    doi: str | None = None
    issn: str | None = None
    isbn: str | None = None

    # Additional fields
    language: str | None = None
    abstract: str | None = None

    # PDFHunter-specific fields
    status: RecordStatus = RecordStatus.NEEDS_REVIEW
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    evidence: list[Evidence] = Field(default_factory=list)
    source_file: str | None = None

    def to_csl_json(self) -> dict[str, Any]:
        """Convert to standard CSL-JSON format."""
        result: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
        }

        if self.title:
            result["title"] = self.title
        if self.author:
            result["author"] = [a.to_csl() for a in self.author]
        if self.issued:
            issued_csl = self.issued.to_csl()
            if issued_csl:
                result["issued"] = issued_csl

        if self.container_title:
            result["container-title"] = self.container_title
        if self.volume:
            result["volume"] = self.volume
        if self.issue:
            result["issue"] = self.issue
        if self.page:
            result["page"] = self.page

        if self.publisher:
            result["publisher"] = self.publisher
        if self.publisher_place:
            result["publisher-place"] = self.publisher_place

        if self.collection_title:
            result["collection-title"] = self.collection_title
        if self.collection_number:
            result["collection-number"] = self.collection_number

        if self.doi:
            result["DOI"] = self.doi
        if self.issn:
            result["ISSN"] = self.issn
        if self.isbn:
            result["ISBN"] = self.isbn

        if self.language:
            result["language"] = self.language

        return result

    def to_zotero_json(self) -> dict[str, Any]:
        """Convert to Zotero-compatible JSON format."""
        # Map internal type to Zotero itemType
        type_mapping = {
            "article": "journalArticle",
            "article-journal": "journalArticle",
            "book": "book",
            "chapter": "bookSection",
            "paper-conference": "conferencePaper",
            "report": "report",
            "thesis": "thesis",
            "patent": "patent",
            "webpage": "webpage",
        }

        result: dict[str, Any] = {
            "itemType": type_mapping.get(self.type, "journalArticle"),
        }

        if self.title:
            result["title"] = self.title

        # Convert authors to Zotero creators format
        if self.author:
            creators = []
            for a in self.author:
                creator: dict[str, str] = {"creatorType": "author"}
                if a.literal:
                    creator["name"] = a.literal
                else:
                    if a.family:
                        creator["lastName"] = a.family
                    if a.given:
                        creator["firstName"] = a.given
                creators.append(creator)
            result["creators"] = creators

        if self.issued and self.issued.year:
            result["date"] = str(self.issued.year)

        if self.container_title:
            # Use appropriate field based on item type
            if result["itemType"] == "journalArticle":
                result["publicationTitle"] = self.container_title
            elif result["itemType"] == "bookSection":
                result["bookTitle"] = self.container_title
            else:
                result["publicationTitle"] = self.container_title

        if self.volume:
            result["volume"] = self.volume
        if self.issue:
            result["issue"] = self.issue
        if self.page:
            result["pages"] = self.page

        if self.publisher:
            result["publisher"] = self.publisher
        if self.publisher_place:
            result["place"] = self.publisher_place

        if self.collection_title:
            result["series"] = self.collection_title
        if self.collection_number:
            result["seriesNumber"] = self.collection_number

        if self.doi:
            result["DOI"] = self.doi
        if self.issn:
            result["ISSN"] = self.issn
        if self.isbn:
            result["ISBN"] = self.isbn

        if self.language:
            result["language"] = self.language

        if self.abstract:
            result["abstractNote"] = self.abstract

        return result

    def get_evidence_for_field(self, field_name: str) -> list[Evidence]:
        """Get all evidence records for a specific field."""
        return [e for e in self.evidence if e.field_name == field_name]

    def calculate_confidence(self) -> float:
        """Calculate overall confidence based on field completeness."""
        required_fields = ["title", "author", "issued"]
        structure_fields = ["container_title", "volume", "issue", "page"]
        publication_fields = ["publisher", "publisher_place"]

        score = 0.0

        # Required fields (0.6 weight)
        required_present = sum(
            1 for f in required_fields if getattr(self, f if f != "issued" else "issued")
        )
        if self.issued and self.issued.year:
            required_present += 0  # Already counted
        score += (required_present / len(required_fields)) * 0.6

        # Structure fields (0.25 weight)
        structure_present = sum(1 for f in structure_fields if getattr(self, f))
        score += (structure_present / len(structure_fields)) * 0.25

        # Publication fields (0.15 weight)
        pub_present = sum(1 for f in publication_fields if getattr(self, f))
        score += (pub_present / len(publication_fields)) * 0.15

        self.confidence = round(score, 2)
        return self.confidence

    def determine_status(self) -> RecordStatus:
        """Determine status based on confidence score."""
        confidence = self.calculate_confidence()

        if confidence >= 0.8:
            self.status = RecordStatus.CONFIRMED
        elif confidence >= 0.4:
            self.status = RecordStatus.NEEDS_REVIEW
        else:
            self.status = RecordStatus.FAILED

        return self.status
