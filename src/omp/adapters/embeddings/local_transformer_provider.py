"""Offline-only local transformer embedding provider for the Alpha runtime."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
import hashlib
import threading
from pathlib import Path
from typing import Any

from omp.application.ports import EmbeddingProfile


class LocalTransformerEmbeddingProvider:
    """Encode E5-style query/passage text from a pinned local model directory.

    The provider never downloads weights.  Loading is explicit and fail-closed:
    the configured directory and its Hugging Face revision metadata must exist
    before the server can become ready.
    """

    def __init__(
        self,
        *,
        model_root: str | Path,
        model_id: str,
        model_revision: str,
        profile_id: str = "semantic",
        profile_version: str = "e5-small-v2-s09",
        dimension: int = 384,
        query_prefix: str = "query: ",
        passage_prefix: str = "passage: ",
        max_length: int = 256,
        cache_size: int = 2048,
    ) -> None:
        if dimension != 384:
            raise ValueError("the Alpha semantic provider requires dimension 384")
        self._root = Path(model_root)
        self._model_id = model_id
        self._model_revision = model_revision
        self._profile = EmbeddingProfile(profile_id, profile_version, dimension, "cosine")
        self._query_prefix = query_prefix
        self._passage_prefix = passage_prefix
        self._max_length = max_length
        self._cache_size = cache_size
        self._cache: OrderedDict[tuple[str, bool], tuple[float, ...]] = OrderedDict()
        self._cache_lock = threading.Lock()
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._torch: Any | None = None
        self._load_lock = threading.Lock()
        self._encode_lock = threading.Lock()

    @property
    def profile(self) -> EmbeddingProfile:
        return self._profile

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def model_revision(self) -> str:
        return self._model_revision

    @property
    def model_root(self) -> Path:
        return self._root

    @property
    def ready(self) -> bool:
        metadata = self._root / ".cache/huggingface/download/model.safetensors.metadata"
        if not self._root.is_dir() or not metadata.is_file():
            return False
        try:
            return metadata.read_text(encoding="utf-8").splitlines()[0] == self._model_revision
        except (OSError, IndexError):
            return False

    async def startup(self) -> None:
        """Load and validate the local model before readiness is advertised."""

        await asyncio.to_thread(self._load)

    async def embed(self, text: str, *, query: bool = False) -> tuple[float, ...]:
        if not text.strip():
            raise ValueError("embedding text must be non-empty")
        key = (text, query)
        with self._cache_lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        vector = await asyncio.to_thread(self._encode, text, query)
        with self._cache_lock:
            self._cache[key] = vector
            if len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
        return vector

    def _load(self) -> None:
        if self._model is not None and self._tokenizer is not None:
            return
        if not self.ready:
            raise RuntimeError("pinned local semantic model is unavailable")
        with self._load_lock:
            if self._model is not None and self._tokenizer is not None:
                return
            try:
                import torch
                from transformers import AutoModel, AutoTokenizer  # type: ignore[import-untyped]
            except ImportError as exc:
                raise RuntimeError("semantic runtime dependencies are not installed") from exc
            self._torch = torch
            self._tokenizer = AutoTokenizer.from_pretrained(
                self._root, local_files_only=True
            )
            self._model = AutoModel.from_pretrained(self._root, local_files_only=True)
            self._model.eval()
            hidden_size = int(self._model.config.hidden_size)
            if hidden_size != self._profile.dimension:
                self._tokenizer = None
                self._model = None
                raise RuntimeError("local semantic model dimension does not match profile")

    def _encode(self, text: str, query: bool) -> tuple[float, ...]:
        self._load()
        assert self._torch is not None
        assert self._model is not None
        assert self._tokenizer is not None
        prefix = self._query_prefix if query else self._passage_prefix
        prepared = f"{prefix}{text}"
        with self._encode_lock:
            encoded = self._tokenizer(
                prepared,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self._max_length,
            )
            with self._torch.inference_mode():
                output = self._model(**encoded).last_hidden_state
            mask = encoded["attention_mask"].unsqueeze(-1).to(output.dtype)
            pooled = (output * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
            normalized = self._torch.nn.functional.normalize(pooled, p=2, dim=1)[0]
            return tuple(float(value) for value in normalized.tolist())

    def artifact_summary(self) -> dict[str, str | int]:
        weight = self._root / "model.safetensors"
        return {
            "model_id": self._model_id,
            "model_revision": self._model_revision,
            "dimension": self._profile.dimension,
            "model_size_bytes": weight.stat().st_size if weight.is_file() else 0,
            "model_safetensors_sha256": (
                hashlib.sha256(weight.read_bytes()).hexdigest() if weight.is_file() else "missing"
            ),
        }
