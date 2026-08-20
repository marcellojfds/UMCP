"""Typed, redaction-safe application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class OMPSettings(BaseSettings):
    """Runtime settings loaded from ``OMP_*`` environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="OMP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "local"
    backend: Literal["postgres", "demo"] = "postgres"
    demo_data_file: str = ".omp/memory.json"
    database_url: SecretStr = SecretStr("postgresql+asyncpg://localhost/omp")
    embedding_profile_id: str = "hash"
    embedding_profile_version: str = "v1"
    embedding_dimension: int = 64
    retrieval_default_threshold: float = 0.78
    retrieval_default_candidate_limit: int = 50
    retrieval_default_limit: int = 5
    migration_head: str = "0002_idempotency_operations"
    log_content: bool = False

    def safe_summary(self) -> dict[str, str | int | float | bool]:
        """Return configuration suitable for diagnostics without secrets."""

        return {
            "environment": self.environment,
            "backend": self.backend,
            "demo_data_file": self.demo_data_file,
            "embedding_profile_id": self.embedding_profile_id,
            "embedding_profile_version": self.embedding_profile_version,
            "embedding_dimension": self.embedding_dimension,
            "retrieval_default_threshold": self.retrieval_default_threshold,
            "retrieval_default_candidate_limit": self.retrieval_default_candidate_limit,
            "retrieval_default_limit": self.retrieval_default_limit,
            "migration_head": self.migration_head,
            "log_content": self.log_content,
        }


@lru_cache(maxsize=1)
def get_settings() -> OMPSettings:
    """Return the process settings; construction has no network side effects."""

    return OMPSettings()
