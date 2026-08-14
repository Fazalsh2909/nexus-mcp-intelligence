"""Credential encryption helpers.

OAuth tokens are encrypted at rest with Fernet before being written to
PostgreSQL, and decrypted only in memory for the duration of an API call.
"""

import json
from typing import Any, Dict

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_credentials(payload: Dict[str, Any]) -> str:
    """Serialize and encrypt a credentials payload (tokens, expiry)."""
    data = json.dumps(payload).encode()
    return _fernet().encrypt(data).decode()


def decrypt_credentials(ciphertext: str) -> Dict[str, Any]:
    """Decrypt a credentials payload previously produced by
    encrypt_credentials. Raises ValueError on bad keys or tampered data."""
    try:
        data = _fernet().decrypt(ciphertext.encode())
    except (InvalidToken, ValueError) as e:
        raise ValueError("Failed to decrypt stored credentials") from e
    return json.loads(data.decode())
