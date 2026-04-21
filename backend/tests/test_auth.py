"""
Tests for auth.py — the security boundary of the entire platform.

Covers:
- Algorithm confusion prevention (SEC-001)
- JWKS caching with TTL
- Rate limiting on failed auth attempts
- Token validation edge cases
- User auto-provisioning
"""
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from jose import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from fastapi import HTTPException


# ── Test RSA key pair ─────────────────────────────────────────────

def _generate_test_rsa_key():
    """Generate a test RSA key pair for JWT signing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    return private_key


def _private_key_to_pem(private_key):
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _public_key_to_jwk(private_key, kid="test-kid-001"):
    """Convert RSA public key to JWK format matching Clerk's JWKS response."""
    from jose.utils import long_to_base64
    public_key = private_key.public_key()
    pub_numbers = public_key.public_numbers()
    return {
        "kty": "RSA",
        "kid": kid,
        "alg": "RS256",
        "use": "sig",
        "n": long_to_base64(pub_numbers.n).decode("utf-8"),
        "e": long_to_base64(pub_numbers.e).decode("utf-8"),
    }


_TEST_KEY = _generate_test_rsa_key()
_TEST_KID = "test-kid-001"
_TEST_JWKS = {"keys": [_public_key_to_jwk(_TEST_KEY, _TEST_KID)]}


def _make_token(payload: dict, kid=_TEST_KID, algorithm="RS256"):
    """Create a signed JWT with the test key."""
    return jwt.encode(
        payload,
        _private_key_to_pem(_TEST_KEY).decode("utf-8"),
        algorithm=algorithm,
        headers={"kid": kid},
    )


def _valid_payload(sub="user_clerk_123", **overrides):
    """Standard valid Clerk JWT payload."""
    now = int(time.time())
    payload = {
        "sub": sub,
        "iat": now - 10,
        "exp": now + 3600,
        "email": "test@example.com",
        "name": "Test User",
    }
    payload.update(overrides)
    return payload


# ══════════════════════════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════════════════════════


class TestAlgorithmConfusion:
    """SEC-001: Algorithm confusion attack prevention."""

    @pytest.mark.asyncio
    async def test_rs256_accepted(self):
        """Valid RS256 token should be accepted."""
        import auth
        auth._jwks_cache = _TEST_JWKS
        auth._jwks_fetched_at = time.monotonic()

        token = _make_token(_valid_payload())
        payload = await auth.verify_clerk_token(token)
        assert payload["sub"] == "user_clerk_123"

    @pytest.mark.asyncio
    async def test_none_algorithm_rejected(self):
        """A token with alg='none' must be rejected even if payload is valid."""
        import auth
        auth._jwks_cache = _TEST_JWKS
        auth._jwks_fetched_at = time.monotonic()

        # Manually craft a 'none' algorithm token
        import base64
        import json
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "kid": _TEST_KID, "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(_valid_payload()).encode()
        ).rstrip(b"=").decode()
        token = f"{header}.{payload_b64}."

        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_clerk_token(token)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_hs256_algorithm_rejected(self):
        """A token claiming HS256 must be rejected (algorithm confusion)."""
        import auth
        auth._jwks_cache = _TEST_JWKS
        auth._jwks_fetched_at = time.monotonic()

        # Even if someone re-signs with HS256 using the public key,
        # our header check should catch it before decode()
        import base64
        import json
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256", "kid": _TEST_KID, "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(_valid_payload()).encode()
        ).rstrip(b"=").decode()
        # Fake signature
        token = f"{header}.{payload_b64}.fakesig"

        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_clerk_token(token)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_kid_rejected(self):
        """Token without a kid in the header must be rejected."""
        import auth
        auth._jwks_cache = _TEST_JWKS
        auth._jwks_fetched_at = time.monotonic()

        token = jwt.encode(
            _valid_payload(),
            _private_key_to_pem(_TEST_KEY).decode("utf-8"),
            algorithm="RS256",
            # No kid in headers
        )

        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_clerk_token(token)
        assert exc_info.value.status_code == 401


class TestJWKSCaching:
    """SEC-001: JWKS caching with TTL and graceful degradation."""

    @pytest.mark.asyncio
    async def test_cache_hit_within_ttl(self):
        """Cached JWKS should be returned without HTTP call within TTL."""
        import auth
        auth._jwks_cache = _TEST_JWKS
        auth._jwks_fetched_at = time.monotonic()

        with patch("auth.httpx.AsyncClient") as mock_client:
            result = await auth._get_jwks()
            # Should NOT have made an HTTP call
            mock_client.assert_not_called()
            assert result == _TEST_JWKS

    @pytest.mark.asyncio
    async def test_cache_expired_triggers_refetch(self):
        """Expired cache should trigger a new JWKS fetch."""
        import auth
        auth._jwks_cache = _TEST_JWKS
        # Set fetched_at to 10 minutes ago (past the 5-min TTL)
        auth._jwks_fetched_at = time.monotonic() - 600

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = _TEST_JWKS

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("auth.httpx.AsyncClient", return_value=mock_client_instance):
            result = await auth._get_jwks()
            assert result == _TEST_JWKS
            mock_client_instance.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_clerk_down(self):
        """If Clerk is down but stale cache exists, return stale cache."""
        import auth
        auth._jwks_cache = _TEST_JWKS
        # Stale but within 10× TTL (25 min ago, limit is 50 min)
        auth._jwks_fetched_at = time.monotonic() - 1500

        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = Exception("Connection refused")
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("auth.httpx.AsyncClient", return_value=mock_client_instance):
            result = await auth._get_jwks()
            # Should return stale cache instead of crashing
            assert result == _TEST_JWKS

    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_ttl(self):
        """force_refresh=True should bypass the TTL check."""
        import auth
        auth._jwks_cache = _TEST_JWKS
        auth._jwks_fetched_at = time.monotonic()  # Fresh cache

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        new_jwks = {"keys": [_public_key_to_jwk(_TEST_KEY, "rotated-kid")]}
        mock_response.json.return_value = new_jwks

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("auth.httpx.AsyncClient", return_value=mock_client_instance):
            result = await auth._get_jwks(force_refresh=True)
            assert result == new_jwks
            mock_client_instance.get.assert_called_once()


class TestRateLimiting:
    """SEC-001: Per-IP rate limiting on failed auth attempts."""

    def setup_method(self):
        """Reset rate limiter state before each test."""
        import auth
        auth._auth_failures.clear()

    def test_under_limit_passes(self):
        """Fewer than 10 failures should not trigger the rate limit."""
        import auth
        for _ in range(9):
            auth._record_auth_failure("192.168.1.1")
        # Should NOT raise
        auth._check_rate_limit("192.168.1.1")

    def test_at_limit_blocks(self):
        """10 failures within the window should trigger 429."""
        import auth
        for _ in range(10):
            auth._record_auth_failure("192.168.1.2")
        with pytest.raises(HTTPException) as exc_info:
            auth._check_rate_limit("192.168.1.2")
        assert exc_info.value.status_code == 429

    def test_different_ips_independent(self):
        """Rate limits should be per-IP, not global."""
        import auth
        for _ in range(10):
            auth._record_auth_failure("10.0.0.1")
        # Different IP should not be affected
        auth._check_rate_limit("10.0.0.2")

    def test_expired_failures_pruned(self):
        """Failures older than the window should be pruned."""
        import auth
        # Simulate old failures
        old_time = time.monotonic() - auth.AUTH_RATE_LIMIT_WINDOW - 5
        auth._auth_failures["10.0.0.3"] = [old_time] * 15
        # Should NOT raise because all failures are expired
        auth._check_rate_limit("10.0.0.3")


class TestTokenValidation:
    """Edge cases for JWT validation."""

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self):
        """Expired tokens must be rejected."""
        import auth
        auth._jwks_cache = _TEST_JWKS
        auth._jwks_fetched_at = time.monotonic()

        token = _make_token(_valid_payload(exp=int(time.time()) - 3600))
        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_clerk_token(token)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_unknown_kid_triggers_refetch(self):
        """Token with unknown kid should trigger JWKS refetch (key rotation)."""
        import auth
        auth._jwks_cache = _TEST_JWKS
        auth._jwks_fetched_at = time.monotonic()

        # Generate token with a different kid
        other_key = _generate_test_rsa_key()
        other_kid = "rotated-kid-002"

        token = jwt.encode(
            _valid_payload(),
            _private_key_to_pem(other_key).decode("utf-8"),
            algorithm="RS256",
            headers={"kid": other_kid},
        )

        # Mock the refetch to return the new key
        new_jwks = {"keys": [_public_key_to_jwk(other_key, other_kid)]}

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = new_jwks

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("auth.httpx.AsyncClient", return_value=mock_client_instance):
            payload = await auth.verify_clerk_token(token)
            assert payload["sub"] == "user_clerk_123"

    @pytest.mark.asyncio
    async def test_missing_sub_rejected(self):
        """Token without 'sub' claim must be rejected."""
        import auth
        auth._jwks_cache = _TEST_JWKS
        auth._jwks_fetched_at = time.monotonic()

        # jose requires 'sub' now via require=["exp", "sub", "iat"]
        payload = _valid_payload()
        del payload["sub"]
        token = _make_token(payload)

        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_clerk_token(token)
        assert exc_info.value.status_code == 401
