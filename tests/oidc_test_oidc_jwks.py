\
import json
import time
import base64
import pytest
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.gateway.dadi_gateway.auth_oidc import OIDCAuthMiddleware


def b64url_uint(val: int) -> str:
    raw = val.to_bytes((val.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def make_rsa_jwk(pubkey, kid: str):
    numbers = pubkey.public_numbers()
    return {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "n": b64url_uint(numbers.n),
        "e": b64url_uint(numbers.e),
    }


def test_oidc_middleware_validates_rs256(monkeypatch):
    # Generate RSA key
    sk = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pk = sk.public_key()
    kid = "k1"
    jwks = {"keys": [make_rsa_jwk(pk, kid)]}

    # Monkeypatch requests.get used under the hood by PyJWT's JWK client (it uses urllib, but PyJWKClient uses requests in newer versions?)
    # PyJWKClient in PyJWT uses urllib.request by default; so we patch jwt.jwks_client.urlopen if present is hard.
    # Instead, we point JWKS URL to a local TestClient endpoint.
    app = FastAPI()

    @app.get("/.well-known/jwks.json")
    def jwks_endpoint():
        return jwks

    # Protected endpoint
    @app.get("/whoami")
    def whoami(request):
        return {"tenant_id": request.state.tenant_id}

    # Mount auth middleware with env config
    import os
    os.environ["DADI_AUTH_MODE"] = "oidc"
    os.environ["DADI_OIDC_ISSUER"] = "https://issuer.example"
    os.environ["DADI_OIDC_AUDIENCE"] = "audience"
    os.environ["DADI_OIDC_JWKS_URL"] = "http://testserver/.well-known/jwks.json"
    os.environ["DADI_TENANT_CLAIM"] = "tenant_id"
    os.environ["DADI_SCOPE_CLAIM"] = "scope"
    os.environ["DADI_CLOCK_SKEW_SECONDS"] = "60"
    os.environ["DADI_JWKS_CACHE_TTL_SECONDS"] = "300"

    app.add_middleware(OIDCAuthMiddleware)
    client = TestClient(app)

    now = int(time.time())
    token = jwt.encode(
        {
            "iss": "https://issuer.example",
            "aud": "audience",
            "exp": now + 300,
            "tenant_id": "tenant_a",
            "scope": "artifact:read_bytes",
        },
        sk.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        algorithm="RS256",
        headers={"kid": kid},
    )

    r = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["tenant_id"] == "tenant_a"
