"""Validation and scoring modules."""

from pdfresolve.validation.scorer import (
    ConfidenceScorer,
    DocumentType,
    FieldScore,
    ScoringResult,
    create_scorer,
)
from pdfresolve.validation.validator import (
    FieldValidator,
    RecordValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    create_validator,
)

__all__ = [
    # Validator
    "FieldValidator",
    "RecordValidator",
    "ValidationIssue",
    "ValidationResult",
    "ValidationSeverity",
    "create_validator",
    # Scorer
    "ConfidenceScorer",
    "DocumentType",
    "FieldScore",
    "ScoringResult",
    "create_scorer",
]
