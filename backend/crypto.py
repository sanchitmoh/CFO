"""
AI CFO — Field-Level Encryption
Fernet-based symmetric encryption for sensitive fields (webhook URLs, API keys).
Key is loaded from the WEBHOOK_ENCRYPTION_KEY environment variable.
"""
import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from config import settings

logger = logging.getLogger(__name__)

# ── Key derivation ────────────────────────────────────────────────
# Fernet requires a 32-byte URL-safe base64-encoded key.
# If the user provides an arbitrary passphrase, we derive a valid key.
# If they provide a proper Fernet key, we use it directly.

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Lazily initialise a Fernet instance from the configured key."""
    global _fernet
    if _fernet is not None:
        return _fernet

    raw_key = settings.WEBHOOK_ENCRYPTION_KEY
    if not raw_key:
        raise RuntimeError(
            "WEBHOOK_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    # Try using the key directly (valid Fernet key)
    try:
        _fernet = Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)
        return _fernet
    except (ValueError, Exception):
        pass

    # Fall back to deriving a key from an arbitrary passphrase
    derived = hashlib.sha256(raw_key.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(derived)
    _fernet = Fernet(key)
    return _fernet


# ── Public API ────────────────────────────────────────────────────

def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value. Returns a base64 Fernet token as a string."""
    if not plaintext:
        return plaintext
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet token back to plaintext."""
    if not ciphertext:
        return ciphertext
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.warning("Failed to decrypt value — may be stored as plaintext (pre-migration)")
        # Return empty rather than leaking a potentially plaintext value
        return ""


def mask_value(value: str | None, visible_chars: int = 8) -> str | None:
    """
    Mask a sensitive string for safe display.
    Example: 'https://hooks.slack.com/services/T00/B00/xxxx' → 'https://...xxxx'
    """
    if not value:
        return None
    if len(value) <= visible_chars:
        return "****"
    return value[:4] + "..." + value[-4:]
