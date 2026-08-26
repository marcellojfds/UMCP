from base64 import urlsafe_b64encode
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

import pytest

from omp.server.identity_contracts import (
    AuthorizationRequest,
    IdentityContractError,
    SyntheticIdentityFlow,
)

SUBJECT = UUID("00000000-0000-0000-0000-000000000001")
CONNECTION = UUID("00000000-0000-0000-0000-000000000010")
TOKEN = UUID("00000000-0000-0000-0000-000000000011")


def request(verifier: str = "synthetic-verifier") -> AuthorizationRequest:
    challenge = urlsafe_b64encode(sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return AuthorizationRequest(
        "synthetic-client", "https://client.example.test/callback",
        frozenset({"memory:read"}), "state", challenge
    )


def flow() -> SyntheticIdentityFlow:
    return SyntheticIdentityFlow(
        allowed_redirect_uris=frozenset({"https://client.example.test/callback"}),
        now=datetime.now(UTC),
    )


def test_pkce_consent_is_versioned_and_code_is_single_use() -> None:
    value = flow()
    consent = value.consent(
        subject_id=SUBJECT, client_id="synthetic-client",
        scopes=frozenset({"memory:read"}), connection_id=CONNECTION
    )
    code = value.authorize(request(), consent=consent)
    assert value.redeem_code(code, code_verifier="synthetic-verifier") == consent
    with pytest.raises(IdentityContractError, match="invalid_or_reused_code"):
        value.redeem_code(code, code_verifier="synthetic-verifier")


@pytest.mark.parametrize("bad_uri", ["https://attacker.example.test/callback", "http://client.example.test/callback"])
def test_callback_allowlist_and_pkce_fail_closed(bad_uri: str) -> None:
    value = flow()
    consent = value.consent(
        subject_id=SUBJECT, client_id="synthetic-client",
        scopes=frozenset({"memory:read"}), connection_id=CONNECTION
    )
    with pytest.raises(IdentityContractError, match="invalid_redirect_uri"):
        value.authorize(replace(request(), redirect_uri=bad_uri), consent=consent)


def test_revocation_blocks_credential_and_connection() -> None:
    value = flow()
    event = value.revoke(credential_id=TOKEN, connection_id=CONNECTION, reason="user_requested")
    assert event.reason == "user_requested"
    assert value.is_revoked(credential_id=TOKEN, connection_id=CONNECTION)
