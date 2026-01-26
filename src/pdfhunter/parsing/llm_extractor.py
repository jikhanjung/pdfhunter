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
    """Result of LLM extraction."""

    title: str | None = None
    author: list[dict[str, str]] = field(default_factory=list)
    container_title: str | None = None
    abstract: str | None = None
    language: str | None = None
    type: str | None = None
    publisher: str | None = None
    year: int | None = None
    volume: str | None = None
    issue: str | None = None
    page: str | None = None

    # Metadata
    model_used: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
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
        return result

    def has_author(self) -> bool:
        """Check if author were extracted."""
        return len(self.author) > 0

    def has_title(self) -> bool:
        """Check if title was extracted."""
        return self.title is not None and len(self.title) > 0


EXTRACTION_PROMPT = """You are a bibliographic metadata extraction expert. Extract bibliographic information from the following text, which comes from a PDF document (possibly OCR'd).

TEXT:
{text}

Extract the following fields if present:
1. title: The title of the work (article, book, report, etc.)
2. author: List of authors with family (last) name and given (first) name(s)
3. container_title: The journal, book, or series title if this is an article or chapter
4. abstract: The abstract if present
5. language: The primary language of the document (use ISO 639-1 codes: en, fr, ru, de, etc.)
6. type: One of: article, book, chapter, report, thesis, proceedings
7. publisher: Name of the publisher
8. year: Publication year (4-digit integer, e.g., 2011)
9. volume: Volume number (e.g., "23" or "XXIII")
10. issue: Issue number (e.g., "4" or "2-3")
11. page: Page range (e.g., "1-25" or "123-145")

Important guidelines:
- For authors, try to separate family and given names. If unclear, use the "literal" field.
- For Cyrillic names, preserve the original script.
- If a field is not present or unclear, leave it as null.
- The title should not include subtitle indicators like volume numbers or dates.
- Container_title is the journal or series name, not the article title.
- Page should be formatted as "start-end" (e.g., "1-25").

CRITICAL for year extraction:
- Extract the PUBLICATION YEAR of THIS document, NOT years from cited references.
- Years appearing as "Author (1990)" or "Smith 1985" are CITATIONS to other works - ignore these.
- Look for the publication year in:
  * Journal citation blocks like "[Palaeontology, Vol.10, 1967, pp. 214-44]"
  * Copyright notices like "© 2020"
  * Header/footer areas with journal info and date
  * Near volume/issue/page information
- If multiple years appear, prefer the one associated with journal/volume/page info.
- Year should be an integer (just the number, not "2011년" or "2011年").

Respond with a JSON object matching this schema:
{{
  "title": "string or null",
  "author": [
    {{"family": "string", "given": "string"}} or {{"literal": "string"}}
  ],
  "container_title": "string or null",
  "abstract": "string or null",
  "language": "string or null",
  "type": "string or null",
  "publisher": "string or null",
  "year": integer or null,
  "volume": "string or null",
  "issue": "string or null",
  "page": "string or null"
}}
"""

EXTRACTION_PROMPT_WITH_IMAGE = """You are a bibliographic metadata extraction expert. Extract bibliographic information from the document page image(s) provided, along with the extracted text below.

TEXT (OCR or extracted):
{text}

Look at the image(s) carefully to extract the following fields. The image may contain information that was not correctly captured in the text (especially for headers, footers, and formatted sections).

Extract the following fields if present:
1. title: The title of the work (article, book, report, etc.)
2. author: List of authors with family (last) name and given (first) name(s)
3. container_title: The journal, book, or series title if this is an article or chapter
4. abstract: The abstract if present
5. language: The primary language of the document (use ISO 639-1 codes: en, fr, ru, de, etc.)
6. type: One of: article, book, chapter, report, thesis, proceedings
7. publisher: Name of the publisher
8. year: Publication year (4-digit integer, e.g., 2011)
9. volume: Volume number (e.g., "23" or "XXIII")
10. issue: Issue number (e.g., "4" or "2-3")
11. page: Page range (e.g., "1-25" or "123-145")

Important guidelines:
- For authors, try to separate family and given names. If unclear, use the "literal" field.
- For Cyrillic names, preserve the original script.
- If a field is not present or unclear, leave it as null.
- The title should not include subtitle indicators like volume numbers or dates.
- Container_title is the journal or series name, not the article title.
- Page should be formatted as "start-end" (e.g., "1-25").
- Pay special attention to journal header/footer information (often contains volume, issue, year, pages).

CRITICAL for year extraction:
- Extract the PUBLICATION YEAR of THIS document, NOT years from cited references.
- Years appearing as "Author (1990)" or "Smith 1985" are CITATIONS to other works - ignore these.
- Look for the publication year in:
  * Journal citation blocks like "[Palaeontology, Vol.10, 1967, pp. 214-44]"
  * Copyright notices like "© 2020"
  * Header/footer areas with journal info and date
  * Near volume/issue/page information
- If multiple years appear, prefer the one associated with journal/volume/page info.
- Year should be an integer (just the number, not "2011년" or "2011年").

Respond with a JSON object matching this schema:
{{
  "title": "string or null",
  "author": [
    {{"family": "string", "given": "string"}} or {{"literal": "string"}}
  ],
  "container_title": "string or null",
  "abstract": "string or null",
  "language": "string or null",
  "type": "string or null",
  "publisher": "string or null",
  "year": integer or null,
  "volume": "string or null",
  "issue": "string or null",
  "page": "string or null"
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

    def extract(self, text: str, max_text_length: int = 4000) -> LLMExtractionResult:
        """Extract bibliographic fields from text.

        Args:
            text: Text to extract from
            max_text_length: Maximum text length to send to LLM

        Returns:
            LLMExtractionResult with extracted fields
        """
        # Truncate text if needed
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."

        prompt = EXTRACTION_PROMPT.format(text=text)

        if self.provider == "openai":
            return self._extract_openai(prompt)
        else:
            return self._extract_anthropic(prompt)

    def extract_with_images(
        self,
        text: str,
        images: list,  # list of PIL.Image objects
        max_text_length: int = 4000,
    ) -> LLMExtractionResult:
        """Extract bibliographic fields from text and images.

        Args:
            text: Text to extract from
            images: List of PIL Image objects (page images)
            max_text_length: Maximum text length to send to LLM

        Returns:
            LLMExtractionResult with extracted fields
        """
        if not images:
            return self.extract(text, max_text_length)

        # Truncate text if needed
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."

        prompt = EXTRACTION_PROMPT_WITH_IMAGE.format(text=text)

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
        """Parse LLM response into result object."""
        result = LLMExtractionResult()

        try:
            # Try to extract JSON from response
            response = response.strip()

            # Handle markdown code blocks
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])

            data = json.loads(response)

            result.title = data.get("title")
            result.container_title = data.get("container_title")
            result.abstract = data.get("abstract")
            result.language = data.get("language")
            result.type = data.get("type")
            result.publisher = data.get("publisher")
            result.volume = data.get("volume")
            result.issue = data.get("issue")
            result.page = data.get("page")

            # Parse year (ensure it's an integer)
            year_val = data.get("year")
            if year_val is not None:
                if isinstance(year_val, int):
                    result.year = year_val
                elif isinstance(year_val, str) and year_val.isdigit():
                    result.year = int(year_val)

            # Parse author
            author_data = data.get("author", [])
            for author in author_data:
                if isinstance(author, dict):
                    author_dict = {}
                    if author.get("family"):
                        author_dict["family"] = author["family"]
                    if author.get("given"):
                        author_dict["given"] = author["given"]
                    if author.get("literal"):
                        author_dict["literal"] = author["literal"]
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
