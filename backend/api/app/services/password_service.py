"""Password hashing và verification sử dụng pwdlib (argon2).

Argon2: Memory-hard algorithm, resistant to GPU/ASIC attacks.
Slow by design (~100ms) để prevent brute-force.
"""
from __future__ import annotations

from pwdlib import PasswordHash

# Singleton hasher với recommended settings (argon2id)
_password_hash = PasswordHash.recommended()


def hash_password(raw_password: str) -> str:
    """Hash password với argon2. ~100ms per hash (intentionally slow)."""
    return _password_hash.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    """Verify password against hash. Returns True nếu match."""
    return _password_hash.verify(raw_password, password_hash)
