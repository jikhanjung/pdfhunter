"""Tests for the main extraction pipeline."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pdfhunter.core.document import Document
from pdfhunter.core.pipeline import Pipeline
from pdfhunter.parsing.llm_extractor import LLMExtractionResult
from pdfhunter.parsing.rule_based import ExtractionResult as RuleResult
from pdfhunter.parsing.patterns import PatternMatch


@pytest.fixture
def dummy_pdf_path() -> Path:
    """Provides the path to the dummy text-based PDF."""
    path = Path("tests/fixtures/dummy_text.pdf")
    if not path.exists():
        pytest.fail(f"Fixture file not found: {path}")
    return path


class TestPipeline:
    def test_pipeline_initialization(self):
        # The constructor now calls the enricher, so we patch it
        with patch("pdfhunter.core.pipeline.WebSearchEnricher"):
            pipeline = Pipeline()
            assert pipeline.config is not None
            assert pipeline.text_extractor is not None
            assert pipeline.ocr_extractor is not None
            assert pipeline.rule_based_extractor is not None
            assert pipeline.llm_extractor is not None
            assert pipeline.merger is not None

    @patch("pdfhunter.enrichment.web_search.scholarly")
    def test_run_pipeline_text_pdf(self, mock_scholarly, dummy_pdf_path):
        """
        Tests the full pipeline run on a text-based PDF with the new evidence flow.
        """
        # 1. Setup
        doc = Document(dummy_pdf_path)
        pipeline = Pipeline(use_mock_llm=True)

        # Mock the document methods for a controlled page-by-page flow
        doc.get_page_indices = MagicMock(return_value=[1, 2])
        doc.extract_text = MagicMock(side_effect=["Text from page 1 with year 2020", "Text from page 2 with volume IX"])

        # Mock the output of the extractors
        pipeline.rule_based_extractor.extract = MagicMock(
            side_effect=[
                RuleResult(matches=[PatternMatch(field_name="year", value="2020", confidence=0.9, raw_match="2020", start=0, end=4, page_number=1)]),
                RuleResult(matches=[PatternMatch(field_name="volume", value="IX", confidence=0.8, raw_match="IX", start=0, end=2, page_number=2)]),
            ]
        )
        pipeline.llm_extractor.extract = MagicMock(
            return_value=LLMExtractionResult(title="LLM Title", author=[{"family": "Doe"}])
        )

        # 2. Run the pipeline
        record = pipeline.run(doc)
        
        # 3. Assertions
        assert record is not None
        assert record.title == "LLM Title"
        assert record.issued and record.issued.year == 2020
        assert record.volume == "IX"
        assert len(record.author) == 1
        assert len(record.evidence) == 2
        assert record.evidence[0].field_name == "year"
        assert record.status is not None
    