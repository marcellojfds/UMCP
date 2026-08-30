from omp.server.oauth import OAuthConfiguration, OAuthServer


def test_authorization_metadata_advertises_rfc_9207_issuer_parameter() -> None:
    config = OAuthConfiguration(
        issuer="https://umcp.example.test", google_client_id="google-client",
        google_client_secret="secret", google_redirect_uri="https://umcp.example.test/oauth/callback",
        clients={"mcp-client": "https://client.example.test/callback"},
        allowed_email_digests=frozenset({"a" * 64}),
    )
    assert OAuthServer(None, config).metadata()["authorization_response_iss_parameter_supported"] is True
