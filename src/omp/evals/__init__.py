"""Versioned evaluation datasets and their offline validation."""

from .dataset import DatasetValidationError, DatasetValidationSummary, validate_retrieval_dataset
from .metrics import (
    QueryOutcome,
    abstention_rate,
    aggregate_metrics,
    intrusion_at_k,
    precision_at_k,
)

__all__ = [
    "DatasetValidationError",
    "DatasetValidationSummary",
    "QueryOutcome",
    "aggregate_metrics",
    "abstention_rate",
    "intrusion_at_k",
    "precision_at_k",
    "validate_retrieval_dataset",
]
