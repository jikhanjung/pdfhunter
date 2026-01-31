"""Tests for the enrichment module."""

import pytest
import uuid
from unittest.mock import patch

from pdfresolve.enrichment.web_search import WebSearchEnricher
from pdfresolve.models.bibliography import BibliographyRecord, Author


class TestWebSearchEnricher:
    def test_enricher_initialization(self):
        enricher = WebSearchEnricher()
        assert enricher is not None

    @patch("pdfresolve.enrichment.web_search.scholarly")
    def test_enrich_with_mock_search(self, mock_scholarly):
        """
        Tests that the enrich method correctly merges data from a web search.
        """
        # Configure the mock to return a dummy publication with new info
        mock_pub = {
            "bib": {
                "title": "A Test Paper",
                "author": ["J. Doe", "A. Nother"],
                "pub_year": "2023",
                "venue": "Journal of Testing",
                "volume": "10",
                "pages": "100-110",
            },
        }
        mock_scholarly.search_single_pub.return_value = mock_pub

        enricher = WebSearchEnricher()
        
        # Create a record that is missing some information
        record = BibliographyRecord(
            id=str(uuid.uuid4()),
            type="article",
            title="A Test Paper",
            author=[Author(family="Doe", given="J.")],
            # 'issued', 'container_title', 'volume', and 'page' are missing
        )
        
        enriched_record = enricher.enrich(record)
        
        # Check that the search was called
        mock_scholarly.search_single_pub.assert_called_once_with("A Test Paper Doe")
        
        # Check that the record was enriched with the new data
        assert enriched_record.issued and enriched_record.issued.year == 2023
        assert enriched_record.container_title == "Journal of Testing"
        assert enriched_record.volume == "10"
        assert enriched_record.page == "100-110"
        
        # The title should be unchanged
        assert enriched_record.title == "A Test Paper"
