"""Accounts: sign in and out, join with an invitation, and the admin's invitations."""

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import auth, config
from app.db import get_session
from app.models import Book, Invite, Term, User

router = APIRouter(prefix="/api")


def _user_out(user: User) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "is_admin": user.is_admin}


@router.get("/auth/me")
def me(request: Request, session: Session = Depends(get_session)):
    """Never 401: the web app asks this first to know the mode and whether to show sign-in."""
    user = auth.user_from_request(request, session)
    return {"mode": config.mode(), "user": _user_out(user) if user else None}


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, session: Session = Depends(get_session)):
    if not config.hosted():
        raise HTTPException(400, "Esta instalación no usa cuentas")
    email = body.email.strip().lower()
    ip = request.client.host if request.client else "?"
    auth.throttle(f"email:{email}", f"ip:{ip}")
    user = auth.find_user(session, email)
    if user is None or not auth.verify_password(user, body.password):
        auth.record_failure(f"email:{email}", f"ip:{ip}")
        raise HTTPException(401, "Correo o contraseña incorrectos")  # never say which one
    auth.start_session(session, response, user)
    return {"user": _user_out(user)}


@router.post("/auth/logout")
def logout(request: Request, response: Response, session: Session = Depends(get_session)):
    auth.end_session(session, request, response)
    return {"ok": True}


@router.get("/auth/invites/{code}")
def check_invite(code: str, session: Session = Depends(get_session)):
    invite = session.get(Invite, code)
    return {"valid": bool(config.hosted() and invite and invite.used_by is None)}


class JoinIn(BaseModel):
    code: str
    email: str
    password: str
    name: str = ""


@router.post("/auth/join")
def join(body: JoinIn, request: Request, response: Response, session: Session = Depends(get_session)):
    if not config.hosted():
        raise HTTPException(400, "Esta instalación no usa cuentas")
    ip = request.client.host if request.client else "?"
    auth.throttle(f"ip:{ip}")
    invite = session.get(Invite, body.code)
    if invite is None or invite.used_by is not None:
        auth.record_failure(f"ip:{ip}")
        raise HTTPException(400, "Esta invitación no es válida o ya se usó")
    email = body.email.strip().lower()
    if "@" not in email or len(email) > 320:
        raise HTTPException(400, "Escribe un correo válido")
    if auth.find_user(session, email):
        raise HTTPException(400, "Ya existe una cuenta con ese correo")
    auth.check_password_rules(body.password)
    user = User(email=email, password_hash=auth.hash_password(body.password), name=body.name.strip()[:100])
    session.add(user)
    session.flush()
    invite.used_by, invite.used_at = user.id, datetime.now(timezone.utc)
    session.commit()
    auth.start_session(session, response, user)
    return {"user": _user_out(user)}


class PasswordIn(BaseModel):
    current: str
    new: str


@router.post("/auth/password")
def change_password(body: PasswordIn, request: Request, response: Response,
                    user: User = Depends(auth.current_user), session: Session = Depends(get_session)):
    if not config.hosted():
        raise HTTPException(400, "Esta instalación no usa cuentas")
    if not auth.verify_password(user, body.current):
        raise HTTPException(400, "La contraseña actual no es correcta")
    auth.check_password_rules(body.new)
    user.password_hash = auth.hash_password(body.new)
    session.commit()
    auth.end_all_sessions(session, user.id)  # signs out every other browser too
    auth.start_session(session, response, user)
    return {"ok": True}


# --- Administration ---------------------------------------------------------------------

class InviteIn(BaseModel):
    note: str = ""


def _invite_out(invite: Invite, emails: dict[int, str]) -> dict:
    return {"code": invite.code, "url": f"{config.public_url()}/join/{invite.code}", "note": invite.note,
            "created_at": invite.created_at.isoformat() if invite.created_at else None,
            "used_by": emails.get(invite.used_by) if invite.used_by else None,
            "used_at": invite.used_at.isoformat() if invite.used_at else None}


@router.get("/admin/invites")
def list_invites(_admin: User = Depends(auth.admin_user), session: Session = Depends(get_session)):
    emails = dict(session.execute(select(User.id, User.email)).all())
    invites = session.scalars(select(Invite).order_by(Invite.created_at.desc())).all()
    return [_invite_out(i, emails) for i in invites]


@router.post("/admin/invites")
def create_invite(body: InviteIn, admin: User = Depends(auth.admin_user), session: Session = Depends(get_session)):
    if not config.hosted():
        raise HTTPException(400, "Esta instalación no usa cuentas")
    invite = Invite(code=secrets.token_urlsafe(12), created_by=admin.id, note=body.note.strip()[:200])
    session.add(invite)
    session.commit()
    return _invite_out(invite, {})


@router.delete("/admin/invites/{code}")
def delete_invite(code: str, _admin: User = Depends(auth.admin_user), session: Session = Depends(get_session)):
    invite = session.get(Invite, code)
    if invite is not None and invite.used_by is None:  # a used one is the account's history
        session.delete(invite)
        session.commit()
    return {"ok": True}


@router.get("/admin/users")
def list_users(_admin: User = Depends(auth.admin_user), session: Session = Depends(get_session)):
    books = dict(session.execute(select(Book.user_id, func.count()).group_by(Book.user_id)).all())
    terms = dict(session.execute(select(Term.user_id, func.count()).group_by(Term.user_id)).all())
    users = session.scalars(select(User).where(User.email.is_not(None)).order_by(User.created_at)).all()
    return [{**_user_out(u), "created_at": u.created_at.isoformat() if u.created_at else None,
             "books": books.get(u.id, 0), "terms": terms.get(u.id, 0)} for u in users]
