"""
AI CFO — Field-Level Encryption
Fernet-based symmetric encryption for sensitive fields (webhook URLs, API keys).
Key is loaded from the WEBHOOK_ENCRYPTION_KEY environment variable.

SEC-FIX: Enhanced key derivation using PBKDF2 for better security.
CRIT-004: Salt loaded from KEY_DERIVATION_SALT env var (random per deployment).
HIGH-005: Fernet fallback catches only ValueError; logs at ERROR level.
MED-003: decrypt_value raises DecryptionError instead of swallowing failures.
"""
import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config import settings

logger = logging.getLogger(__name__)


# ── Custom exception ──────────────────────────────────────────────
class DecryptionError(Exception):
    """Raised when a ciphertext cannot be decrypted.

    Callers must handle this explicitly — returning empty strings or
    silently swallowing decryption failures leads to data loss.
    """


# ── Key derivation ────────────────────────────────────────────────
# Fernet requires a 32-byte URL-safe base64-encoded key.
# If the user provides an arbitrary passphrase, we derive a valid key using PBKDF2.
# If they provide a proper Fernet key, we use it directly.

_fernet: Fernet | None = None

# CRIT-004: Salt MUST come from an environment variable — never hardcoded.
# Generate a random value per deployment:
#   python -c "import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
_KEY_DERIVATION_SALT: bytes | None = None

_PBKDF2_ITERATIONS = 480000  # OWASP recommended minimum for 2024


def _load_salt() -> bytes:
    """Load the KDF salt from the environment, failing hard if missing."""
    global _KEY_DERIVATION_SALT
    if _KEY_DERIVATION_SALT is not None:
        return _KEY_DERIVATION_SALT

    raw = settings.KEY_DERIVATION_SALT
    if not raw:
        raise RuntimeError(
            "KEY_DERIVATION_SALT is not set. "
            "Generate one with: python -c \"import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())\""
        )

    # Accept base64-encoded or raw UTF-8 bytes
    try:
        _KEY_DERIVATION_SALT = base64.urlsafe_b64decode(raw)
    except Exception:
        _KEY_DERIVATION_SALT = raw.encode("utf-8")

    if len(_KEY_DERIVATION_SALT) < 16:
        raise RuntimeError(
            "KEY_DERIVATION_SALT is too short (minimum 16 bytes). "
            "Generate a proper salt with: python -c \"import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())\""
        )

    return _KEY_DERIVATION_SALT


def _get_fernet() -> Fernet:
    """Lazily initialise a Fernet instance from the configured key.

    HIGH-005: Only catches ValueError when testing for a raw Fernet key.
    Logs at ERROR level before falling back to PBKDF2 derivation.
    """
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
    # HIGH-005: Only catch ValueError — the only expected exception for an
    # invalid-format key.  Do NOT catch Exception broadly; MemoryError,
    # KeyboardInterrupt, import errors etc. must propagate.
    try:
        _fernet = Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)
        return _fernet
    except ValueError:
        logger.error(
            "WEBHOOK_ENCRYPTION_KEY is not a valid Fernet key — "
            "falling back to PBKDF2 key derivation.  For production, "
            "generate a proper Fernet key to avoid this fallback."
        )

    # CRIT-004: Use per-deployment salt from the environment
    salt = _load_salt()

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    derived = kdf.derive(raw_key.encode("utf-8"))
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
    """Decrypt a Fernet token back to plaintext.

    MED-003: Raises ``DecryptionError`` on failure so callers can handle
    it explicitly.  Never returns an empty string on error — that masks
    data loss and can cause downstream requests to ``localhost``.

    Raises:
        DecryptionError: If the ciphertext cannot be decrypted (wrong key,
            corrupted data, or plaintext value that was never encrypted).
    """
    if not ciphertext:
        return ciphertext
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.error(
            "Failed to decrypt value — token is invalid (wrong key or corrupted data)"
        )
        raise DecryptionError(
            "Cannot decrypt value. The encryption key may have changed, "
            "or the stored value was never encrypted."
        )


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
