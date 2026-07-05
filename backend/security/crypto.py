"""
Credential Encryption
======================
User ka GitHub Personal Access Token aur Groq API Key kabhi bhi plaintext
me disk/DB (AsyncSqliteStore) me store nahi hoga. Yaha Fernet (AES-128-CBC +
HMAC, symmetric, authenticated encryption) use kiya gaya hai.

Setup:
    .env me ek APP_ENCRYPTION_KEY hona chahiye. Generate karne ke liye:

        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    Ye key kabhi bhi git me commit mat karo, aur agar ye key rotate/lose ho gayi
    to purane encrypted tokens decrypt nahi ho payenge (user ko dubara token
    dena hoga) — isliye is key ka secure backup rakho (e.g. secret manager).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


class CredentialCipherError(Exception):
    pass


class CredentialCipher:
    """Thin wrapper around Fernet for encrypting/decrypting single credential strings."""

    def __init__(self, key: Optional[str] = None):
        raw_key = key or os.getenv("APP_ENCRYPTION_KEY")
        if not raw_key:
            raise CredentialCipherError(
                "APP_ENCRYPTION_KEY missing hai. .env me ek Fernet key set karo:\n"
                "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        try:
            self._fernet = Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)
        except Exception as e:
            raise CredentialCipherError(f"Invalid APP_ENCRYPTION_KEY: {e}")

    def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        """None-safe encrypt. Returns None if input is None/empty."""
        if not plaintext:
            return None
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, ciphertext: Optional[str]) -> Optional[str]:
        """None-safe decrypt. Returns None if input is None/empty or invalid/corrupted."""
        if not ciphertext:
            return None
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            # Corrupted ciphertext ya galat/rotated key — fail safe, treat as missing.
            return None


@lru_cache(maxsize=1)
def get_cipher() -> CredentialCipher:
    """Process-wide singleton so Fernet object baar baar re-create na ho (cheap hai but still)."""
    return CredentialCipher()