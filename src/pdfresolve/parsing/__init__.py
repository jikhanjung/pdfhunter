"""Parsing modules for rule-based and LLM extraction."""

from pdfresolve.parsing.patterns import (
    PatternMatch,
    is_valid_year,
    normalize_page_range,
    roman_to_int,
)
from pdfresolve.parsing.rule_based import (
    ExtractionResult,
    RuleBasedExtractor,
    create_rule_based_extractor,
)
from pdfresolve.parsing.llm_extractor import (
    LLMExtractionResult,
    LLMExtractor,
    MockLLMExtractor,
    create_llm_extractor,
)

__all__ = [
    # Patterns
    "PatternMatch",
    "is_valid_year",
    "normalize_page_range",
    "roman_to_int",
    # Rule-based extraction
    "ExtractionResult",
    "RuleBasedExtractor",
    "create_rule_based_extractor",
    # LLM extraction
    "LLMExtractionResult",
    "LLMExtractor",
    "MockLLMExtractor",
    "create_llm_extractor",
]
