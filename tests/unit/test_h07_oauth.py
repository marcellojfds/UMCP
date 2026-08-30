from __future__ import annotations

import json

from pydantic import SecretStr

from omp.config import OMPSettings
from omp.server.oauth import (
    CHATGPT_CLIENT_ID,
    CHATGPT_REDIRECT_URI,
    OAuthConfiguration,
    OAuthServer,
    _pkce,
    _valid_pkce_challenge,
)


def settings(**overrides: object) -> OMPSettings:
    values: dict[str, object] = {
        "environment": "cloud",
        "public_base_url": "https://staging.example.test",
        "oauth_google_credentials": SecretStr("google-client-secret"),
        "oauth_google_client_id": "public-client-id.apps.googleusercontent.com",
        "oauth_google_redirect_uri": "https://staging.example.test/oauth/callback",
        "oauth_clients": json.dumps({"mcp-client": "https://client.example.test/callback"}),
        "oauth_allowed_email_sha256": "a" * 64,
    }
    values.update(overrides)
    return OMPSettings(**values)


def test_oauth_configuration_requires_all_explicit_public_bindings() -> None:
    config = OAuthConfiguration.from_settings(settings())

    assert config is not None
    assert config.google_client_id == "public-client-id.apps.googleusercontent.com"
    assert config.google_redirect_uri == "https://staging.example.test/oauth/callback"
    assert config.clients == {"mcp-client": "https://client.example.test/callback"}
    assert config.allowed_email_digests == frozenset({"a" * 64})


def test_oauth_configuration_fails_closed_for_missing_or_ambiguous_values() -> None:
    invalid = [
        {"oauth_google_client_id": ""},
        {"oauth_google_redirect_uri": ""},
        {"oauth_clients": ""},
        {"oauth_clients": json.dumps({"mcp-client": "http://client.example.test/callback"})},
        {"oauth_allowed_email_sha256": ""},
        {"oauth_allowed_email_sha256": "not-a-sha256"},
        {"public_base_url": "http://staging.example.test"},
    ]

    assert all(OAuthConfiguration.from_settings(settings(**case)) is None for case in invalid)


def test_oauth_configuration_accepts_multiple_explicitly_allowed_users() -> None:
    config = OAuthConfiguration.from_settings(
        settings(oauth_allowed_email_sha256="a" * 64 + "," + "b" * 64)
    )

    assert config is not None
    assert config.allowed_email_digests == frozenset({"a" * 64, "b" * 64})


def test_oauth_configuration_rejects_google_bundle_with_different_explicit_client_id() -> None:
    bundle = json.dumps(
        {
            "web": {
                "client_id": "different.apps.googleusercontent.com",
                "client_secret": "google-client-secret",
            }
        }
    )

    assert OAuthConfiguration.from_settings(
        settings(oauth_google_credentials=SecretStr(bundle))
    ) is None


def test_oauth_configuration_repr_does_not_contain_client_secret() -> None:
    config = OAuthConfiguration.from_settings(settings())

    assert config is not None
    assert "google-client-secret" not in repr(config)


def test_pkce_s256_is_strict_and_does_not_accept_malformed_challenges() -> None:
    verifier = "v" * 64
    challenge = _pkce(verifier)

    assert _valid_pkce_challenge(challenge)
    assert len(challenge) == 43
    assert not _valid_pkce_challenge(challenge + "=")
    assert not _valid_pkce_challenge("!")


def test_chatgpt_client_metadata_id_is_bound_to_the_official_redirect() -> None:
    config = OAuthConfiguration.from_settings(settings())

    assert config is not None
    server = OAuthServer(object(), config)  # type: ignore[arg-type]
    assert server._client_redirect_allowed(CHATGPT_CLIENT_ID, CHATGPT_REDIRECT_URI)
    assert not server._client_redirect_allowed(
        CHATGPT_CLIENT_ID, "https://attacker.example.test/callback"
    )
