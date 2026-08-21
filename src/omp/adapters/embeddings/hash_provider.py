"""Offline deterministic embedding provider for the MVP baseline and tests."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence

from omp.application.ports import EmbeddingProfile


class HashEmbeddingProvider:
    """A dependency-free, versioned feature-hash embedding.

    This is intentionally a baseline adapter, not a claim of semantic quality.
    It makes local development and tests deterministic without a model download
    or an external provider. A production provider can implement the same port.
    """

    def __init__(
        self, *, dimension: int = 64, profile_id: str = "hash", version: str = "v1"
    ) -> None:
        self._profile = EmbeddingProfile(
            id=profile_id,
            version=version,
            dimension=dimension,
            metric="cosine",
        )

    @property
    def profile(self) -> EmbeddingProfile:
        return self._profile

    async def embed(self, text: str, *, query: bool = False) -> Sequence[float]:
        tokens = re.findall(r"[\wÀ-ÿ]+", text.casefold())
        vector = [0.0] * self._profile.dimension
        for token in tokens:
            self._add_feature(vector, token, weight=1.0)
        for left, right in zip(tokens, tokens[1:], strict=False):
            self._add_feature(vector, f"{left}:{right}", weight=0.5)
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return tuple(0.0 for _ in vector)
        return tuple(value / norm for value in vector)

    def _add_feature(self, vector: list[float], feature: str, *, weight: float) -> None:
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % len(vector)
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign * weight
