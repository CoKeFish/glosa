"""API keys entered in the app, stored encrypted.

Keys from the environment (Doppler) always win; a key saved in the app is the fallback for
people who run glosa without a secrets manager. Stored keys are encrypted with Fernet. The
master key comes from GLOSA_SECRET_KEY, or is generated once and kept in a file on its own
volume, so a database dump alone does not reveal the API keys.
"""

import os
from functools import cache
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.models import ApiKey

KEY_FILE = Path(os.environ.get("GLOSA_KEY_FILE", "/data/secret.key"))


@cache
def _fernet() -> Fernet:
    configured = os.environ.get("GLOSA_SECRET_KEY")
    if configured:
        return Fernet(configured.encode())
    if not KEY_FILE.exists():
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        KEY_FILE.write_bytes(Fernet.generate_key())
        KEY_FILE.chmod(0o600)
    return Fernet(KEY_FILE.read_bytes().strip())


def save_key(session: Session, provider: str, key: str) -> None:
    token = _fernet().encrypt(key.strip().encode()).decode()
    session.merge(ApiKey(provider=provider, encrypted=token, hint=key.strip()[-4:]))
    session.commit()


def delete_key(session: Session, provider: str) -> None:
    row = session.get(ApiKey, provider)
    if row is not None:
        session.delete(row)
        session.commit()


def stored_key(session: Session, provider: str) -> str | None:
    row = session.get(ApiKey, provider)
    if row is None:
        return None
    try:
        return _fernet().decrypt(row.encrypted.encode()).decode()
    except InvalidToken:
        return None  # master key changed: the stored key is unreadable and must be entered again


def stored_hint(session: Session, provider: str) -> str | None:
    row = session.get(ApiKey, provider)
    return row.hint if row else None
