"""Tests for parsing modules."""

import os
import pytest

from pdfhunter.parsing.patterns import (
    PatternMatch,
    is_valid_year,
    normalize_page_range,
    roman_to_int,
)
from pdfhunter.parsing.rule_based import (
    ExtractionResult,
    RuleBasedExtractor,
    create_rule_based_extractor,
)
from pdfhunter.parsing.llm_extractor import (
    LLMExtractionResult,
    LLMExtractor,
    MockLLMExtractor,
    create_llm_extractor,
)

# Helper to check for API key
has_openai_key = "OPENAI_API_KEY" in os.environ
skip_if_no_openai_key = pytest.mark.skipif(
    not has_openai_key, reason="OPENAI_API_KEY not set"
)

class TestPatternMatch:
    def test_create_match(self):
        match = PatternMatch(
            field_name="year",
            value="2023",
            raw_match="(2023)",
            start=10,
            end=16,
            confidence=0.9,
            pattern_name="year_parentheses",
        )
        assert match.field_name == "year"
        assert match.value == "2023"
        assert match.confidence == 0.9

    def test_match_to_dict(self):
        match = PatternMatch(
            field_name="pages",
            value="123-456",
            raw_match="pp. 123-456",
            start=0,
            end=11,
        )
        d = match.to_dict()

        assert d["field_name"] == "pages"
        assert d["value"] == "123-456"
        assert d["raw_match"] == "pp. 123-456"


class TestPatternUtilities:
    def test_roman_to_int(self):
        assert roman_to_int("I") == 1
        assert roman_to_int("IV") == 4
        assert roman_to_int("V") == 5
        assert roman_to_int("IX") == 9
        assert roman_to_int("X") == 10
        assert roman_to_int("XL") == 40
        assert roman_to_int("L") == 50
        assert roman_to_int("XC") == 90
        assert roman_to_int("C") == 100
        assert roman_to_int("CD") == 400
        assert roman_to_int("D") == 500
        assert roman_to_int("CM") == 900
        assert roman_to_int("M") == 1000
        assert roman_to_int("MCMXCIX") == 1999
        assert roman_to_int("MMXXIII") == 2023

    def test_roman_to_int_lowercase(self):
        assert roman_to_int("iv") == 4
        assert roman_to_int("xii") == 12

    def test_normalize_page_range(self):
        assert normalize_page_range("123", "456") == "123-456"
        assert normalize_page_range("1", "10") == "1-10"

    def test_is_valid_year(self):
        assert is_valid_year(2023) is True
        assert is_valid_year(1850) is True
        assert is_valid_year(1500) is True
        assert is_valid_year(1499) is False
        assert is_valid_year(2031) is False


class TestExtractionResult:
    def test_empty_result(self):
        result = ExtractionResult()
        assert result.year is None
        assert result.pages is None
        assert result.field_count() == 0

    def test_result_with_fields(self):
        result = ExtractionResult(
            year=2023,
            pages="123-456",
            volume="10",
            issue="2",
        )
        assert result.field_count() == 4

    def test_result_to_dict(self):
        result = ExtractionResult(
            year=2020,
            pages="50-75",
            volume="5",
        )
        d = result.to_dict()

        assert d["year"] == 2020
        assert d["pages"] == "50-75"
        assert d["volume"] == "5"
        assert "issue" not in d

    def test_get_matches_for_field(self):
        matches = [
            PatternMatch("year", "2020", "2020", 0, 4),
            PatternMatch("year", "2021", "2021", 10, 14),
            PatternMatch("pages", "1-10", "pp. 1-10", 20, 29),
        ]
        result = ExtractionResult(matches=matches)

        year_matches = result.get_matches_for_field("year")
        assert len(year_matches) == 2

        page_matches = result.get_matches_for_field("pages")
        assert len(page_matches) == 1


class TestRuleBasedExtractor:
    def test_create_extractor(self):
        extractor = RuleBasedExtractor()
        assert extractor.extract_all_matches is True
        assert extractor.min_confidence == 0.5

    def test_extract_year_standard(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("Published in 2023")
        assert result.year == 2023

    def test_extract_year_parentheses(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("Journal of Science (2021)")
        assert result.year == 2021

    def test_extract_year_copyright(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("© 2019 Publisher Inc.")
        assert result.year == 2019

    def test_extract_pages_standard(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("pp. 123-456")
        assert result.pages == "123-456"

    def test_extract_pages_single_p(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("p. 50-75")
        assert result.pages == "50-75"

    def test_extract_pages_colon(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("10: 234-256")
        assert result.pages == "234-256"

    def test_extract_volume_standard(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("Vol. 15")
        assert result.volume == "15"

    def test_extract_volume_roman(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("tome IX")
        assert result.volume == "9"

    def test_extract_volume_russian(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("Том 5")
        assert result.volume == "5"

    def test_extract_issue_standard(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("No. 3")
        assert result.issue == "3"

    def test_extract_issue_numero(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("n° 12")
        assert result.issue == "12"

    def test_extract_issue_russian(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("Выпуск 7")
        assert result.issue == "7"

    def test_extract_place_major(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("Published in Paris")
        assert result.place == "Paris"

    def test_extract_place_russian(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("Издано в Ленинграде")
        assert result.place is not None
        assert "Ленинград" in result.place

    def test_extract_doi(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("DOI: 10.1234/journal.2023.001")
        assert result.doi == "10.1234/journal.2023.001"

    def test_extract_issn(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("ISSN 1234-5678")
        assert result.issn == "1234-5678"

    def test_extract_isbn(self):
        extractor = create_rule_based_extractor()
        result = extractor.extract("ISBN 978-3-16-148410-0")
        assert result.isbn is not None

    def test_extract_multiple_fields(self):
        extractor = create_rule_based_extractor()
        text = "Bull. Soc. géol. France (7), IX, 1967, p. 750–757, Paris"
        result = extractor.extract(text)

        assert result.year == 1967
        assert result.pages is not None
        assert result.volume == "9"  # IX converted
        assert result.place == "Paris"

    def test_extract_russian_text(self):
        extractor = create_rule_based_extractor()
        text = "Труды института, Том 15, Выпуск 3, с. 45-67, Москва, 1985"
        result = extractor.extract(text)

        assert result.year == 1985
        assert result.volume == "15"
        assert result.issue == "3"
        assert result.place == "Москва"

    def test_matches_preserved(self):
        extractor = create_rule_based_extractor(extract_all_matches=True)
        result = extractor.extract("Vol. 10, 2020, 2021")

        # Should have matches for both years
        year_matches = result.get_matches_for_field("year")
        assert len(year_matches) >= 2


class TestRuleBasedExtractorFactory:
    def test_create_default(self):
        extractor = create_rule_based_extractor()
        assert isinstance(extractor, RuleBasedExtractor)

    def test_create_with_options(self):
        extractor = create_rule_based_extractor(
            extract_all_matches=False,
            min_confidence=0.8,
        )
        assert extractor.extract_all_matches is False
        assert extractor.min_confidence == 0.8


# LLM Extractor Tests
class TestLLMExtractionResult:
    def test_empty_result(self):
        result = LLMExtractionResult()
        assert result.title is None
        assert result.author == []
        assert not result.has_title()
        assert not result.has_author()

    def test_result_with_data(self):
        result = LLMExtractionResult(
            title="Test Article",
            author=[{"family": "Smith", "given": "John"}],
            container_title="Test Journal",
            language="en",
            type="article",
        )
        assert result.has_title()
        assert result.has_author()
        assert len(result.author) == 1

    def test_result_to_dict(self):
        result = LLMExtractionResult(
            title="Test",
            author=[{"family": "Doe", "given": "Jane"}],
        )
        d = result.to_dict()

        assert d["title"] == "Test"
        assert len(d["author"]) == 1
        assert "abstract" not in d  # None values not included

    def test_result_to_dict_empty(self):
        result = LLMExtractionResult()
        d = result.to_dict()
        assert d == {}


class TestMockLLMExtractor:
    def test_mock_default_response(self):
        mock = MockLLMExtractor()
        result = mock.extract("Some text")

        assert result.model_used == "mock"
        assert mock.call_count == 1
        assert mock.last_text == "Some text"

    def test_mock_with_pattern_response(self):
        mock = MockLLMExtractor(
            responses={
                "Smith": LLMExtractionResult(
                    title="Test Paper",
                    author=[{"family": "Smith", "given": "John"}],
                ),
            }
        )

        result = mock.extract("Paper by Smith et al.")
        assert result.title == "Test Paper"
        assert result.author[0]["family"] == "Smith"

    def test_mock_no_match(self):
        mock = MockLLMExtractor(
            responses={
                "specific": LLMExtractionResult(title="Matched"),
            }
        )

        result = mock.extract("other text")
        assert result.title is None

    def test_mock_call_count(self):
        mock = MockLLMExtractor()
        mock.extract("text 1")
        mock.extract("text 2")
        mock.extract("text 3")

        assert mock.call_count == 3

    def test_mock_extract_with_images(self):
        """Test that extract_with_images delegates to extract."""
        mock = MockLLMExtractor(
            responses={
                "Smith": LLMExtractionResult(
                    title="Paper with Images",
                    author=[{"family": "Smith", "given": "Jane"}],
                ),
            }
        )

        # Create a simple fake image (just a mock object)
        class FakeImage:
            pass

        fake_images = [FakeImage(), FakeImage()]

        result = mock.extract_with_images("Paper by Smith", fake_images)
        assert result.title == "Paper with Images"
        assert mock.call_count == 1

    def test_mock_extract_with_images_empty_list(self):
        """Test extract_with_images with no images."""
        mock = MockLLMExtractor()
        result = mock.extract_with_images("Some text", [])
        assert result.model_used == "mock"


class TestLLMExtractor:
    def test_create_extractor_openai(self):
        extractor = LLMExtractor(provider="openai")
        assert extractor.provider == "openai"
        assert extractor.model == "gpt-4o-mini"

    def test_create_extractor_anthropic(self):
        extractor = LLMExtractor(provider="anthropic")
        assert extractor.provider == "anthropic"
        assert extractor.model == "claude-3-haiku-20240307"

    def test_create_extractor_custom_model(self):
        extractor = LLMExtractor(provider="openai", model="gpt-4o")
        assert extractor.model == "gpt-4o"

    def test_parse_response_valid_json(self):
        extractor = LLMExtractor()
        response = '''
        {
            "title": "Test Article",
            "author": [{"family": "Smith", "given": "John"}],
            "container_title": "Journal of Testing",
            "language": "en",
            "type": "article"
        }
        '''
        result = extractor._parse_response(response)

        assert result.title == "Test Article"
        assert len(result.author) == 1
        assert result.author[0]["family"] == "Smith"
        assert result.container_title == "Journal of Testing"
        assert result.language == "en"

    def test_parse_response_with_markdown(self):
        extractor = LLMExtractor()
        response = '''```json
        {"title": "Markdown Test", "author": []}
        ```'''
        result = extractor._parse_response(response)

        assert result.title == "Markdown Test"

    def test_parse_response_invalid_json(self):
        extractor = LLMExtractor()
        response = "This is not JSON"
        result = extractor._parse_response(response)

        assert result.title is None
        assert result.author == []

    def test_parse_response_cyrillic_authors(self):
        extractor = LLMExtractor()
        response = '''
        {
            "title": "Исследование",
            "author": [{"family": "Иванов", "given": "Иван"}],
            "language": "ru"
        }
        '''
        result = extractor._parse_response(response)

        assert result.title == "Исследование"
        assert result.author[0]["family"] == "Иванов"
        assert result.language == "ru"

    def test_parse_response_literal_author(self):
        extractor = LLMExtractor()
        response = '''
        {
            "title": "Test",
            "author": [{"literal": "Anonymous"}]
        }
        '''
        result = extractor._parse_response(response)

        assert result.author[0]["literal"] == "Anonymous"

    def test_encode_image_to_base64(self):
        """Test image encoding to base64."""
        from PIL import Image
        import io

        extractor = LLMExtractor()

        # Create a small test image
        img = Image.new("RGB", (100, 100), color="red")

        base64_str = extractor._encode_image_to_base64(img)

        # Verify it's a valid base64 string
        assert isinstance(base64_str, str)
        assert len(base64_str) > 0

        # Verify it can be decoded back
        import base64
        decoded = base64.b64decode(base64_str)
        assert decoded[:2] == b"\xff\xd8"  # JPEG magic bytes

    def test_encode_image_to_base64_rgba(self):
        """Test encoding RGBA image (converts to RGB)."""
        from PIL import Image

        extractor = LLMExtractor()

        # Create RGBA image
        img = Image.new("RGBA", (50, 50), color=(255, 0, 0, 128))

        base64_str = extractor._encode_image_to_base64(img)
        assert isinstance(base64_str, str)
        assert len(base64_str) > 0

    def test_extract_with_images_no_images(self):
        """Test extract_with_images falls back to text-only when no images."""
        extractor = LLMExtractor()

        # Mock the _extract_openai method to avoid actual API call
        called_with_text = []

        def mock_extract(text, max_text_length=4000, pdf_metadata=None):
            called_with_text.append(text)
            return LLMExtractionResult(title="Mocked")

        extractor.extract = mock_extract

        result = extractor.extract_with_images("Test text", [])
        assert result.title == "Mocked"
        assert "Test text" in called_with_text[0]


class TestLLMExtractorFactory:
    def test_create_default(self):
        extractor = create_llm_extractor()
        assert isinstance(extractor, LLMExtractor)

    def test_create_mock(self):
        extractor = create_llm_extractor(use_mock=True)
        assert isinstance(extractor, MockLLMExtractor)

    def test_create_with_provider(self):
        extractor = create_llm_extractor(provider="anthropic")
        assert extractor.provider == "anthropic"


# Integration tests - require actual API keys
@pytest.mark.integration
class TestLLMExtractorIntegration:
    """Integration tests that require API access."""

    @skip_if_no_openai_key
    def test_extract_with_openai(self):
        """Test extraction with real OpenAI API."""
        text = """
        Journal of Cognitive Science, Vol. 28, No. 3, pp. 451-468 (2023)
        Attention is All You Need
        Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit,
        Llion Jones, Aidan N. Gomez, Lukasz Kaiser, and Illia Polosukhin
        Google Brain & Google Research
        av@google.com, noam@google.com
        """
        extractor = create_llm_extractor(provider="openai")
        result = extractor.extract(text)

        assert result.title.lower() == "attention is all you need"
        assert result.has_author()
        assert len(result.author) == 8
        assert any(
            author["family"].lower() == "vaswani" for author in result.author
        )
        assert result.container_title == "Journal of Cognitive Science"
        assert result.model_used.startswith("gpt")

    def test_extract_with_anthropic(self):
        """Test extraction with real Anthropic API."""
        pass
