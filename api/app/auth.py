"""Who is asking. In self-hosted mode always the local user; on the hosted service, the
account behind the session cookie.

Passwords are hashed with argon2. A session is a random token in an HttpOnly cookie; the
database keeps only its SHA-256, so a stolen database cannot be replayed as sessions. The
cookie is SameSite=Lax, so other sites cannot make the browser send it with a POST, and
state-changing requests from another origin are refused as well (see main.check_origin).
"""

import hashlib
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import config
from app.db import get_session
from app.models import LOCAL_USER_ID, AuthSession, User

COOKIE = "glosa_session"
SESSION_DAYS = 30
MIN_PASSWORD = 10
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(user: User, password: str) -> bool:
    if not user.password_hash:
        return False
    try:
        return _hasher.verify(user.password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def check_password_rules(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise HTTPException(400, f"La contraseña necesita al menos {MIN_PASSWORD} caracteres")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(session: Session, response: Response, user: User) -> None:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    session.add(AuthSession(token_hash=_token_hash(token), user_id=user.id, expires_at=expires))
    session.commit()
    response.set_cookie(COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True, samesite="lax",
                        secure=config.secure_cookies(), path="/")


def end_session(session: Session, request: Request, response: Response) -> None:
    token = request.cookies.get(COOKIE)
    if token:
        session.execute(delete(AuthSession).where(AuthSession.token_hash == _token_hash(token)))
        session.commit()
    response.delete_cookie(COOKIE, path="/")


def end_all_sessions(session: Session, user_id: int) -> None:
    session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
    session.commit()


def user_from_request(request: Request, session: Session) -> User | None:
    if not config.hosted():
        return session.get(User, LOCAL_USER_ID)
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    row = session.get(AuthSession, _token_hash(token))
    if row is None:
        return None
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        session.delete(row)
        session.commit()
        return None
    return session.get(User, row.user_id)


def current_user(request: Request, session: Session = Depends(get_session)) -> User:
    user = user_from_request(request, session)
    if user is None:
        raise HTTPException(401, "Inicia sesión para continuar")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Solo la administración puede hacer esto")
    return user


def find_user(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email.strip().lower()))


# Brute force: after 8 failed attempts on an address (or from an IP) in 15 minutes, wait.
_failures: dict[str, list[float]] = {}
_lock = threading.Lock()
WINDOW, LIMIT = 15 * 60, 8


def throttle(*keys: str) -> None:
    now = time.monotonic()
    with _lock:
        for key in keys:
            recent = [t for t in _failures.get(key, []) if now - t < WINDOW]
            _failures[key] = recent
            if len(recent) >= LIMIT:
                raise HTTPException(429, "Demasiados intentos. Espera unos minutos y vuelve a probar.")


def record_failure(*keys: str) -> None:
    with _lock:
        for key in keys:
            _failures.setdefault(key, []).append(time.monotonic())
