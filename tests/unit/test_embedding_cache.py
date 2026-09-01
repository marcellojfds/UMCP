from __future__ import annotations

import pytest

from omp.adapters.embeddings.hash_provider import HashEmbeddingProvider


@pytest.mark.asyncio
async def test_hash_embedding_provider_caches_repeat_calls() -> None:
    provider = HashEmbeddingProvider(dimension=64, cache_size=2)
    vec1 = await provider.embed("user preference: python")
    assert len(vec1) == 64
    assert ("user preference: python", False) in provider._cache

    # Second call hits the in-memory cache
    vec2 = await provider.embed("user preference: python")
    assert vec1 == vec2

    # Query embedding uses different key
    vec_query = await provider.embed("user preference: python", query=True)
    assert len(provider._cache) == 2

    # Adding a 3rd unique text evicts the oldest (LRU)
    await provider.embed("third text")
    assert len(provider._cache) == 2
    assert ("user preference: python", False) not in provider._cache
