"""
Secure credential generation for accounts created by an admin on someone
else's behalf (currently: Parent accounts). Not a password *policy*
module - just generates strong random values; hashing/storage still goes
through the normal User.set_password()/password_hash flow, and nothing
here ever writes a plaintext password anywhere persistent (DB, logs).
"""
import secrets
import string

from app.models import User

_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%&*"


def generate_temp_password(length=10) -> str:
    """Cryptographically random temporary password. Guarantees at least
    one lowercase, one uppercase, one digit, and one symbol so it passes
    typical complexity checks, then fills the rest randomly and shuffles."""
    if length < 4:
        length = 4
    required = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%&*"),
    ]
    remaining = [secrets.choice(_PASSWORD_ALPHABET) for _ in range(length - len(required))]
    chars = required + remaining
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def generate_unique_username(base: str) -> str:
    """e.g. base="parent" -> "parent4821" - random enough to avoid
    collisions without leaking any personal info (unlike a name-derived
    username, which could expose a child's name/relationship publicly)."""
    base = "".join(ch for ch in base.lower() if ch.isalnum()) or "parent"
    for _ in range(20):
        candidate = f"{base}{secrets.randbelow(90000) + 10000}"
        if not User.query.filter_by(username=candidate).first():
            return candidate
    # Extremely unlikely fallback if 20 random attempts all collided.
    return f"{base}{secrets.token_hex(4)}"
