"""Embedding provider adapters."""

from .hash_provider import HashEmbeddingProvider
from .local_transformer_provider import LocalTransformerEmbeddingProvider

__all__ = ["HashEmbeddingProvider", "LocalTransformerEmbeddingProvider"]
