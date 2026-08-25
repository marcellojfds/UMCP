"""Typed synthetic connector fixtures and local conformance adapters."""

from .fixtures import (
    CHATGPT_SIM,
    CLAUDE_SIM,
    CONSENT,
    PROVENANCE,
    READER_SIM,
    TENANT_B_SIM,
    ConnectorFixture,
)
from .local_adapter import ConnectorContractError, SyntheticLocalAdapter

__all__ = [
    "CHATGPT_SIM",
    "CLAUDE_SIM",
    "CONSENT",
    "ConnectorContractError",
    "ConnectorFixture",
    "PROVENANCE",
    "READER_SIM",
    "SyntheticLocalAdapter",
    "TENANT_B_SIM",
]
