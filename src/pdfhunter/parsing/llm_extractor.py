"""LLM-based extraction of bibliographic fields."""

import base64
import io
import json
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

try:
    from PIL import Image
except ImportError:
    Image = None


class AuthorSchema(BaseModel):
    """Schema for author extraction."""

    family: str | None = Field(None, description="Family/last name")
    given: str | None = Field(None, description="Given/first name(s)")
    literal: str | None = Field(None, description="Full name if cannot be parsed")


class LLMExtractionSchema(BaseModel):
    """Schema for LLM extraction output."""

    title: str | None = Field(None, description="Title of the work")
    authors: list[AuthorSchema] = Field(default_factory=list, description="List of authors")
    container_title: str | None = Field(
        None, description="Journal, book, or series title containing this work"
    )
    abstract: str | None = Field(None, description="Abstract if present")
    language: str | None = Field(None, description="Primary language (ISO 639-1 code)")
    type: str | None = Field(
        None, description="Type: article, book, chapter, report, thesis"
    )
    publisher: str | None = Field(None, description="Publisher name")
    year: int | None = Field(None, description="Publication year")
    volume: str | None = Field(None, description="Volume number")
    issue: str | None = Field(None, description="Issue number")
    page: str | None = Field(None, description="Page range (e.g., '1-25')")


@dataclass
class LLMExtractionResult:
    """Result of LLM extraction with Zotero-compatible fields."""

    # Zotero-compatible fields
    title: str | None = None
    author: list[dict[str, str]] = field(default_factory=list)  # [{lastName, firstName} or {name}]
    container_title: str | None = None  # publicationTitle in Zotero
    abstract: str | None = None  # abstractNote in Zotero
    language: str | None = None
    type: str | None = None  # itemType in Zotero
    publisher: str | None = None
    year: int | None = None  # date in Zotero
    volume: str | None = None
    issue: str | None = None
    page: str | None = None  # pages in Zotero
    series: str | None = None
    series_number: str | None = None
    doi: str | None = None
    issn: str | None = None
    isbn: str | None = None

    # Metadata
    model_used: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (internal field names)."""
        result = {}
        if self.title:
            result["title"] = self.title
        if self.author:
            result["author"] = self.author
        if self.container_title:
            result["container_title"] = self.container_title
        if self.abstract:
            result["abstract"] = self.abstract
        if self.language:
            result["language"] = self.language
        if self.type:
            result["type"] = self.type
        if self.publisher:
            result["publisher"] = self.publisher
        if self.year:
            result["year"] = self.year
        if self.volume:
            result["volume"] = self.volume
        if self.issue:
            result["issue"] = self.issue
        if self.page:
            result["page"] = self.page
        if self.series:
            result["series"] = self.series
        if self.series_number:
            result["series_number"] = self.series_number
        if self.doi:
            result["doi"] = self.doi
        if self.issn:
            result["issn"] = self.issn
        if self.isbn:
            result["isbn"] = self.isbn
        return result

    def to_zotero_dict(self) -> dict[str, Any]:
        """Convert to Zotero-compatible dictionary."""
        result: dict[str, Any] = {}
        if self.type:
            result["itemType"] = self.type
        if self.title:
            result["title"] = self.title
        if self.author:
            # Convert to Zotero creators format
            creators = []
            for a in self.author:
                creator = {"creatorType": "author"}
                if "lastName" in a or "family" in a:
                    creator["lastName"] = a.get("lastName") or a.get("family", "")
                    creator["firstName"] = a.get("firstName") or a.get("given", "")
                elif "name" in a or "literal" in a:
                    creator["name"] = a.get("name") or a.get("literal", "")
                creators.append(creator)
            result["creators"] = creators
        if self.container_title:
            result["publicationTitle"] = self.container_title
        if self.abstract:
            result["abstractNote"] = self.abstract
        if self.language:
            result["language"] = self.language
        if self.publisher:
            result["publisher"] = self.publisher
        if self.year:
            result["date"] = str(self.year)
        if self.volume:
            result["volume"] = self.volume
        if self.issue:
            result["issue"] = self.issue
        if self.page:
            result["pages"] = self.page
        if self.series:
            result["series"] = self.series
        if self.series_number:
            result["seriesNumber"] = self.series_number
        if self.doi:
            result["DOI"] = self.doi
        if self.issn:
            result["ISSN"] = self.issn
        if self.isbn:
            result["ISBN"] = self.isbn
        return result

    def has_author(self) -> bool:
        """Check if author were extracted."""
        return len(self.author) > 0

    def has_title(self) -> bool:
        """Check if title was extracted."""
        return self.title is not None and len(self.title) > 0


EXTRACTION_PROMPT = """You are a bibliographic metadata extraction expert. Extract bibliographic information from the following text for importing into Zotero reference manager.

TEXT:
{text}

{pdf_metadata}

Extract the following Zotero-compatible fields:
1. itemType: One of: journalArticle, book, bookSection, conferencePaper, report, thesis, patent, webpage
2. title: The title of the work
3. creators: List of authors with lastName and firstName
4. publicationTitle: Journal name (for journalArticle) or book title (for bookSection)
5. abstractNote: The abstract if present
6. language: Primary language (ISO 639-1: en, fr, ru, de, etc.)
7. publisher: Publisher name
8. date: Publication year (4-digit integer)
9. volume: Volume number
10. issue: Issue number
11. pages: Page range (e.g., "1-25")
12. series: Series name if applicable
13. seriesNumber: Series number if applicable
14. DOI: Digital Object Identifier if present
15. ISSN: For journals
16. ISBN: For books

Important guidelines:
- For creators, separate lastName and firstName. If unclear, use "name" field for full name.
- For Cyrillic names, preserve the original script.
- If a field is not present or unclear, leave it as null.
- The title should not include subtitle indicators like volume numbers or dates.
- publicationTitle is the journal/book name, not the article title.
- pages should be formatted as "start-end" (e.g., "1-25").

CRITICAL for date/year extraction:
- Extract the PUBLICATION YEAR of THIS document, NOT years from cited references.
- Years appearing as "Author (1990)" or "Smith 1985" are CITATIONS to other works - ignore these.
- Look for the publication year in:
  * Journal citation blocks like "[Palaeontology, Vol.10, 1967, pp. 214-44]"
  * Copyright notices like "© 2020"
  * Header/footer areas with journal info and date
  * Near volume/issue/page information
- If multiple years appear, prefer the one associated with journal/volume/page info.
- Year should be an integer (just the number, not "2011년" or "2011年").

Respond with a JSON object matching this Zotero-compatible schema:
{{
  "itemType": "journalArticle|book|bookSection|conferencePaper|report|thesis",
  "title": "string or null",
  "creators": [
    {{"lastName": "string", "firstName": "string", "creatorType": "author"}} or {{"name": "string", "creatorType": "author"}}
  ],
  "publicationTitle": "string or null",
  "abstractNote": "string or null",
  "language": "string or null",
  "publisher": "string or null",
  "date": integer or null,
  "volume": "string or null",
  "issue": "string or null",
  "pages": "string or null",
  "series": "string or null",
  "seriesNumber": "string or null",
  "DOI": "string or null",
  "ISSN": "string or null",
  "ISBN": "string or null"
}}
"""

EXTRACTION_PROMPT_WITH_IMAGE = """You are a bibliographic metadata extraction expert. Extract bibliographic information from the document page image(s) provided for importing into Zotero reference manager.

TEXT (OCR or extracted):
{text}

{pdf_metadata}

Look at the image(s) carefully to extract bibliographic metadata. The image may contain information that was not correctly captured in the text (especially for headers, footers, and formatted sections like journal citation blocks).

Extract the following Zotero-compatible fields:
1. itemType: One of: journalArticle, book, bookSection, conferencePaper, report, thesis, patent, webpage
2. title: The title of the work
3. creators: List of authors with lastName and firstName
4. publicationTitle: Journal name (for journalArticle) or book title (for bookSection)
5. abstractNote: The abstract if present
6. language: Primary language (ISO 639-1: en, fr, ru, de, etc.)
7. publisher: Publisher name
8. date: Publication year (4-digit integer)
9. volume: Volume number
10. issue: Issue number
11. pages: Page range (e.g., "1-25")
12. series: Series name if applicable
13. seriesNumber: Series number if applicable
14. DOI: Digital Object Identifier if present
15. ISSN: For journals
16. ISBN: For books

Important guidelines:
- For creators, separate lastName and firstName. If unclear, use "name" field for full name.
- For Cyrillic names, preserve the original script.
- If a field is not present or unclear, leave it as null.
- The title should not include subtitle indicators like volume numbers or dates.
- publicationTitle is the journal/book name, not the article title.
- pages should be formatted as "start-end" (e.g., "1-25").
- Pay special attention to journal header/footer information (often contains volume, issue, year, pages).

CRITICAL for date/year extraction:
- Extract the PUBLICATION YEAR of THIS document, NOT years from cited references.
- Years appearing as "Author (1990)" or "Smith 1985" are CITATIONS to other works - ignore these.
- Look for the publication year in:
  * Journal citation blocks like "[Palaeontology, Vol.10, 1967, pp. 214-44]"
  * Copyright notices like "© 2020"
  * Header/footer areas with journal info and date
  * Near volume/issue/page information
- If multiple years appear, prefer the one associated with journal/volume/page info.
- Year should be an integer (just the number, not "2011년" or "2011年").

Respond with a JSON object matching this Zotero-compatible schema:
{{
  "itemType": "journalArticle|book|bookSection|conferencePaper|report|thesis",
  "title": "string or null",
  "creators": [
    {{"lastName": "string", "firstName": "string", "creatorType": "author"}} or {{"name": "string", "creatorType": "author"}}
  ],
  "publicationTitle": "string or null",
  "abstractNote": "string or null",
  "language": "string or null",
  "publisher": "string or null",
  "date": integer or null,
  "volume": "string or null",
  "issue": "string or null",
  "pages": "string or null",
  "series": "string or null",
  "seriesNumber": "string or null",
  "DOI": "string or null",
  "ISSN": "string or null",
  "ISBN": "string or null"
}}
"""


class LLMExtractor:
    """Extract bibliographic fields using LLM."""

    def __init__(
        self,
        provider: Literal["openai", "anthropic"] = "openai",
        model: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ):
        """Initialize LLM extractor.

        Args:
            provider: LLM provider ('openai' or 'anthropic')
            model: Model name (default depends on provider)
            api_key: API key (or use environment variable)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key

        # Set default models
        if model is None:
            if provider == "openai":
                self.model = "gpt-4o-mini"
            else:
                self.model = "claude-3-haiku-20240307"
        else:
            self.model = model

        self._client = None

    def _get_openai_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            from openai import OpenAI

            if self.api_key:
                self._client = OpenAI(api_key=self.api_key)
            else:
                self._client = OpenAI()  # Uses OPENAI_API_KEY env var
        return self._client

    def _get_anthropic_client(self):
        """Get or create Anthropic client."""
        if self._client is None:
            from anthropic import Anthropic

            if self.api_key:
                self._client = Anthropic(api_key=self.api_key)
            else:
                self._client = Anthropic()  # Uses ANTHROPIC_API_KEY env var
        return self._client

    def extract(
        self,
        text: str,
        max_text_length: int = 4000,
        pdf_metadata: dict | None = None,
    ) -> LLMExtractionResult:
        """Extract bibliographic fields from text.

        Args:
            text: Text to extract from
            max_text_length: Maximum text length to send to LLM
            pdf_metadata: Optional PDF metadata dict to include in prompt

        Returns:
            LLMExtractionResult with extracted fields
        """
        # Truncate text if needed
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."

        # Format PDF metadata if available
        pdf_meta_str = ""
        if pdf_metadata:
            meta_parts = []
            if pdf_metadata.get("title"):
                meta_parts.append(f"PDF Title: {pdf_metadata['title']}")
            if pdf_metadata.get("author"):
                meta_parts.append(f"PDF Author: {pdf_metadata['author']}")
            if pdf_metadata.get("subject"):
                meta_parts.append(f"PDF Subject: {pdf_metadata['subject']}")
            if pdf_metadata.get("keywords"):
                meta_parts.append(f"PDF Keywords: {pdf_metadata['keywords']}")
            if pdf_metadata.get("creation_date"):
                meta_parts.append(f"PDF Creation Date: {pdf_metadata['creation_date']}")
            if meta_parts:
                pdf_meta_str = "PDF METADATA (use as hints, may be incomplete or incorrect):\n" + "\n".join(meta_parts)

        prompt = EXTRACTION_PROMPT.format(text=text, pdf_metadata=pdf_meta_str)

        if self.provider == "openai":
            return self._extract_openai(prompt)
        else:
            return self._extract_anthropic(prompt)

    def extract_with_images(
        self,
        text: str,
        images: list,  # list of PIL.Image objects
        max_text_length: int = 4000,
        pdf_metadata: dict | None = None,
    ) -> LLMExtractionResult:
        """Extract bibliographic fields from text and images.

        Args:
            text: Text to extract from
            images: List of PIL Image objects (page images)
            max_text_length: Maximum text length to send to LLM
            pdf_metadata: Optional PDF metadata dict to include in prompt

        Returns:
            LLMExtractionResult with extracted fields
        """
        if not images:
            return self.extract(text, max_text_length, pdf_metadata)

        # Truncate text if needed
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."

        # Format PDF metadata if available
        pdf_meta_str = ""
        if pdf_metadata:
            meta_parts = []
            if pdf_metadata.get("title"):
                meta_parts.append(f"PDF Title: {pdf_metadata['title']}")
            if pdf_metadata.get("author"):
                meta_parts.append(f"PDF Author: {pdf_metadata['author']}")
            if pdf_metadata.get("subject"):
                meta_parts.append(f"PDF Subject: {pdf_metadata['subject']}")
            if pdf_metadata.get("keywords"):
                meta_parts.append(f"PDF Keywords: {pdf_metadata['keywords']}")
            if pdf_metadata.get("creation_date"):
                meta_parts.append(f"PDF Creation Date: {pdf_metadata['creation_date']}")
            if meta_parts:
                pdf_meta_str = "PDF METADATA (use as hints, may be incomplete or incorrect):\n" + "\n".join(meta_parts)

        prompt = EXTRACTION_PROMPT_WITH_IMAGE.format(text=text, pdf_metadata=pdf_meta_str)

        if self.provider == "openai":
            return self._extract_openai_with_images(prompt, images)
        else:
            return self._extract_anthropic_with_images(prompt, images)

    def _encode_image_to_base64(self, image) -> str:
        """Encode PIL Image to base64 string."""
        if Image is None:
            raise ImportError("Pillow is required for image encoding")

        buffer = io.BytesIO()
        # Convert to RGB if necessary (handle RGBA, grayscale, etc.)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")

    def _extract_openai(self, prompt: str) -> LLMExtractionResult:
        """Extract using OpenAI API."""
        client = self._get_openai_client()

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a bibliographic metadata extraction expert. Always respond with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
        )

        raw_response = response.choices[0].message.content or "{}"

        result = self._parse_response(raw_response)
        result.model_used = self.model
        result.raw_response = raw_response

        if response.usage:
            result.prompt_tokens = response.usage.prompt_tokens
            result.completion_tokens = response.usage.completion_tokens

        return result

    def _extract_anthropic(self, prompt: str) -> LLMExtractionResult:
        """Extract using Anthropic API."""
        client = self._get_anthropic_client()

        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
            system="You are a bibliographic metadata extraction expert. Always respond with valid JSON only, no other text.",
        )

        raw_response = response.content[0].text if response.content else "{}"

        result = self._parse_response(raw_response)
        result.model_used = self.model
        result.raw_response = raw_response

        if response.usage:
            result.prompt_tokens = response.usage.input_tokens
            result.completion_tokens = response.usage.output_tokens

        return result

    def _extract_openai_with_images(
        self, prompt: str, images: list
    ) -> LLMExtractionResult:
        """Extract using OpenAI API with images.

        Args:
            prompt: Text prompt
            images: List of PIL Image objects

        Returns:
            LLMExtractionResult with extracted fields
        """
        client = self._get_openai_client()

        # Build content array with text and images
        content = [{"type": "text", "text": prompt}]

        for image in images:
            base64_image = self._encode_image_to_base64(image)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",
                    "detail": "high",
                },
            })

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a bibliographic metadata extraction expert. Always respond with valid JSON.",
                },
                {"role": "user", "content": content},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
        )

        raw_response = response.choices[0].message.content or "{}"

        result = self._parse_response(raw_response)
        result.model_used = self.model
        result.raw_response = raw_response

        if response.usage:
            result.prompt_tokens = response.usage.prompt_tokens
            result.completion_tokens = response.usage.completion_tokens

        return result

    def _extract_anthropic_with_images(
        self, prompt: str, images: list
    ) -> LLMExtractionResult:
        """Extract using Anthropic API with images.

        Args:
            prompt: Text prompt
            images: List of PIL Image objects

        Returns:
            LLMExtractionResult with extracted fields
        """
        client = self._get_anthropic_client()

        # Build content array with images first, then text
        content = []

        for image in images:
            base64_image = self._encode_image_to_base64(image)
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64_image,
                },
            })

        content.append({"type": "text", "text": prompt})

        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": content}],
            system="You are a bibliographic metadata extraction expert. Always respond with valid JSON only, no other text.",
        )

        raw_response = response.content[0].text if response.content else "{}"

        result = self._parse_response(raw_response)
        result.model_used = self.model
        result.raw_response = raw_response

        if response.usage:
            result.prompt_tokens = response.usage.input_tokens
            result.completion_tokens = response.usage.output_tokens

        return result

    def _parse_response(self, response: str) -> LLMExtractionResult:
        """Parse LLM response into result object (handles both old and Zotero field names)."""
        result = LLMExtractionResult()

        try:
            # Try to extract JSON from response
            response = response.strip()

            # Handle markdown code blocks
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])

            data = json.loads(response)

            # Title
            result.title = data.get("title")

            # Container title (Zotero: publicationTitle, old: container_title)
            result.container_title = data.get("publicationTitle") or data.get("container_title")

            # Abstract (Zotero: abstractNote, old: abstract)
            result.abstract = data.get("abstractNote") or data.get("abstract")

            result.language = data.get("language")

            # Type (Zotero: itemType, old: type)
            item_type = data.get("itemType") or data.get("type")
            if item_type:
                # Map Zotero itemType to internal type
                type_mapping = {
                    "journalArticle": "article",
                    "book": "book",
                    "bookSection": "chapter",
                    "conferencePaper": "paper-conference",
                    "report": "report",
                    "thesis": "thesis",
                    "patent": "patent",
                    "webpage": "webpage",
                }
                result.type = type_mapping.get(item_type, item_type)

            result.publisher = data.get("publisher")
            result.volume = data.get("volume")
            result.issue = data.get("issue")

            # Pages (Zotero: pages, old: page)
            result.page = data.get("pages") or data.get("page")

            # Series
            result.series = data.get("series")
            result.series_number = data.get("seriesNumber") or data.get("series_number")

            # Identifiers
            result.doi = data.get("DOI") or data.get("doi")
            result.issn = data.get("ISSN") or data.get("issn")
            result.isbn = data.get("ISBN") or data.get("isbn")

            # Parse year/date (Zotero: date, old: year)
            year_val = data.get("date") or data.get("year")
            if year_val is not None:
                if isinstance(year_val, int):
                    result.year = year_val
                elif isinstance(year_val, str):
                    # Try to extract year from date string
                    year_str = year_val.strip()
                    if year_str.isdigit() and len(year_str) == 4:
                        result.year = int(year_str)
                    else:
                        # Try to find 4-digit year in string
                        import re
                        match = re.search(r'\b(19|20)\d{2}\b', year_str)
                        if match:
                            result.year = int(match.group())

            # Parse authors/creators
            # Zotero format: creators with lastName/firstName or name
            # Old format: author with family/given or literal
            creators = data.get("creators", [])
            authors = data.get("author", [])

            for creator in creators:
                if isinstance(creator, dict):
                    author_dict = {}
                    if creator.get("lastName"):
                        author_dict["family"] = creator["lastName"]
                    if creator.get("firstName"):
                        author_dict["given"] = creator["firstName"]
                    if creator.get("name"):
                        author_dict["literal"] = creator["name"]
                    if author_dict:
                        result.author.append(author_dict)

            for author in authors:
                if isinstance(author, dict):
                    author_dict = {}
                    if author.get("family") or author.get("lastName"):
                        author_dict["family"] = author.get("family") or author.get("lastName")
                    if author.get("given") or author.get("firstName"):
                        author_dict["given"] = author.get("given") or author.get("firstName")
                    if author.get("literal") or author.get("name"):
                        author_dict["literal"] = author.get("literal") or author.get("name")
                    if author_dict:
                        result.author.append(author_dict)

        except json.JSONDecodeError:
            # Failed to parse JSON
            pass

        return result


class MockLLMExtractor:
    """Mock LLM extractor for testing without API calls."""

    def __init__(self, responses: dict[str, LLMExtractionResult] | None = None):
        """Initialize mock extractor.

        Args:
            responses: Dict mapping text patterns to responses
        """
        self.responses = responses or {}
        self.call_count = 0
        self.last_text = ""

    def extract(self, text: str, max_text_length: int = 4000) -> LLMExtractionResult:
        """Mock extraction.

        Args:
            text: Text to extract from
            max_text_length: Maximum text length (ignored in mock)

        Returns:
            LLMExtractionResult (from predefined or default)
        """
        self.call_count += 1
        self.last_text = text

        # Check for matching pattern
        for pattern, response in self.responses.items():
            if pattern in text:
                return response

        # Return default empty result
        return LLMExtractionResult(model_used="mock")

    def extract_with_images(
        self,
        text: str,
        images: list,
        max_text_length: int = 4000,
    ) -> LLMExtractionResult:
        """Mock extraction with images (images are ignored).

        Args:
            text: Text to extract from
            images: List of PIL Image objects (ignored in mock)
            max_text_length: Maximum text length (ignored in mock)

        Returns:
            LLMExtractionResult (from predefined or default)
        """
        # Just delegate to text-only extraction
        return self.extract(text, max_text_length)


def create_llm_extractor(
    provider: Literal["openai", "anthropic"] = "openai",
    model: str | None = None,
    api_key: str | None = None,
    use_mock: bool = False,
) -> LLMExtractor | MockLLMExtractor:
    """Factory function to create an LLM extractor.

    Args:
        provider: LLM provider
        model: Model name
        api_key: API key
        use_mock: Use mock extractor for testing

    Returns:
        LLMExtractor or MockLLMExtractor instance
    """
    if use_mock:
        return MockLLMExtractor()

    return LLMExtractor(
        provider=provider,
        model=model,
        api_key=api_key,
    )
