"""Tests for the Merger class."""

import pytest

from pdfresolve.core.merger import Merger
from pdfresolve.parsing.rule_based import ExtractionResult as RuleResult
from pdfresolve.parsing.llm_extractor import LLMExtractionResult as LLMResult
from pdfresolve.models.bibliography import DateParts
from pdfresolve.parsing.patterns import PatternMatch

class TestMerger:

    def test_merger_initialization(self):
        merger = Merger()
        assert merger is not None

    def test_priority_merge_strategy(self):
        """
        Tests the priority-based merging strategy.
        """
        merger = Merger()
        
        # Create rule-based results from multiple pages
        rule_results = [
            RuleResult(matches=[
                PatternMatch(field_name="year", value="2020", confidence=0.9, raw_match="2020", start=0, end=4),
                PatternMatch(field_name="volume", value="IX", confidence=0.8, raw_match="vol. IX", start=0, end=7),
            ]),
            RuleResult(matches=[
                PatternMatch(field_name="year", value="2021", confidence=0.7, raw_match="(2021)", start=0, end=6), # Lower confidence
                PatternMatch(field_name="doi", value="10.1234/rule.doi", confidence=0.95, raw_match="doi:...", start=0, end=10),
            ]),
        ]
        
        # Create an LLM result
        llm_result = LLMResult(
            title="LLM Title",
            author=[{"family": "LLM", "given": "Author"}],
            container_title="LLM Journal",
        )
        
        merged_data, all_evidence = merger.merge(rule_results, llm_result)
        
        # Assertions
        assert len(all_evidence) == 4 # Check that all evidence was collected

        # Check that the highest confidence rule match was chosen and LLM fields were used
        assert merged_data["title"] == "LLM Title"
        assert len(merged_data["author"]) == 1
        assert merged_data["container_title"] == "LLM Journal"
        assert merged_data["volume"] == "IX" # Rule-based result has priority
        assert merged_data["doi"] == "10.1234/rule.doi"
        
        # Check that year was correctly handled and converted to a DateParts object
        assert "year" not in merged_data
        assert "issued" in merged_data
        assert isinstance(merged_data["issued"], DateParts)
        assert merged_data["issued"].year == 2020 # Highest confidence rule-based year is chosen
