"""Local-only composition for the future hosted MCP trust boundary.

This module deliberately creates only the private ``/_hosted_boundary`` test
seam.  It does not mount Streamable HTTP, publish ``/mcp``, configure a
network listener, or provide an identity-provider implementation.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from fastapi import FastAPI

from omp.adapters.mcp.hosted import (
    HostedMCPAdapter,
    HostedMemoryService,
    create_hosted_boundary_app,
)
from omp.server.hosted_auth import CredentialVerifier, HostedAuthenticator


def create_local_hosted_gateway(
    service: HostedMemoryService,
    verifier: CredentialVerifier,
    *,
    issuer: str,
    audience: str,
    clock: Callable[[], datetime] | None = None,
    request_id_factory: Callable[[], str] | None = None,
) -> FastAPI:
    """Compose injected hosted dependencies into an internal-only ASGI seam.

    ``verifier`` must already have verified every accepted credential.  The
    resulting app remains useful only for local/in-process tests: it exposes
    neither a public MCP endpoint nor an IdP, credential issuer, or deployment
    configuration.
    """

    authenticator = HostedAuthenticator(
        verifier,
        issuer=issuer,
        audience=audience,
        clock=clock,
        request_id_factory=request_id_factory,
    )
    return create_hosted_boundary_app(HostedMCPAdapter(service, authenticator))


__all__ = ["create_local_hosted_gateway"]
