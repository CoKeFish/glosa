import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app import settings_store, srs
from app.auth import current_user
from app.db import get_session
from app.models import IGNORED, KINDS, KNOWN, LEARNING, Term, User
from app.routers.common import normalize_key, own_term, require_language, term_out

router = APIRouter(prefix="/api")

VALID_STATUSES = {IGNORED, *LEARNING, KNOWN}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TermIn(BaseModel):
    language: str
    key: str
    kind: str = "word"
    status: int | None = None
    meaning: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    context: str | None = None


def _apply(term: Term, body: "TermIn | TermPatch") -> None:
    for field in ("meaning", "notes", "tags", "context"):
        value = getattr(body, field)
        if value is not None:
            setattr(term, field, value)
    if body.status is not None:
        if body.status not in VALID_STATUSES:
            raise HTTPException(400, f"Estado inválido: {body.status}")
        srs.set_status(term, body.status, _now())


@router.put("/terms")
def upsert_term(body: TermIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Create or update by (language, key): the reader does not need to know if the term exists."""
    require_language(body.language)
    if body.kind not in KINDS:
        raise HTTPException(400, f"Tipo inválido: {body.kind}")
    key = normalize_key(body.key)
    term = session.scalar(select(Term).where(Term.user_id == user.id, Term.language == body.language, Term.key == key))
    if term is None:
        term = Term(user_id=user.id, language=body.language, key=key, kind=body.kind, meaning="", notes="", tags=[], context="")
        srs.set_status(term, body.status if body.status is not None else 1, _now())
        session.add(term)
    _apply(term, body)
    session.commit()
    return term_out(term)


class TermPatch(BaseModel):
    status: int | None = None
    meaning: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    context: str | None = None


@router.patch("/terms/{term_id}")
def patch_term(term_id: int, body: TermPatch, user: User = Depends(current_user),
               session: Session = Depends(get_session)):
    term = own_term(session, user.id, term_id)
    _apply(term, body)
    session.commit()
    return term_out(term)


@router.delete("/terms/{term_id}")
def delete_term(term_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    term = own_term(session, user.id, term_id)
    session.delete(term)
    session.commit()
    return {"ok": True}


@router.get("/terms")
def list_terms(
    language: str,
    status: int | None = None,
    kind: str | None = None,
    q: str | None = None,
    due: bool = False,
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    query = select(Term).where(Term.user_id == user.id, Term.language == language)
    if status is not None:
        query = query.where(Term.status == status)
    else:
        query = query.where(Term.status.in_(LEARNING))  # known and ignored only on request
    if kind:
        query = query.where(Term.kind == kind)
    if q:
        like = f"%{q.lower()}%"
        query = query.where(or_(Term.key.like(like), func.lower(Term.meaning).like(like)))
    if due:
        query = query.where(Term.srs_due <= _now())
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    rows = session.scalars(query.order_by(Term.updated_at.desc()).limit(limit).offset(offset)).all()
    return {"total": total, "items": [term_out(t) for t in rows]}


class KeysIn(BaseModel):
    language: str
    keys: list[str]


@router.post("/terms/mark-known")
def mark_known(body: KeysIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Page turn: every word still new on the page becomes known. Returns what changed, for undo."""
    keys = {normalize_key(k) for k in body.keys}
    existing = set(session.scalars(
        select(Term.key).where(Term.user_id == user.id, Term.language == body.language, Term.key.in_(keys))))
    created = sorted(keys - existing)
    for key in created:
        session.add(Term(user_id=user.id, language=body.language, key=key, kind="word", status=KNOWN, meaning="", notes="",
                         tags=[], context=""))
    session.commit()
    return {"created": created}


@router.post("/terms/undo-known")
def undo_known(body: KeysIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    keys = [normalize_key(k) for k in body.keys]
    result = session.execute(
        delete(Term).where(Term.user_id == user.id, Term.language == body.language, Term.key.in_(keys),
                           Term.status == KNOWN)
    )
    session.commit()
    return {"deleted": result.rowcount}


@router.get("/terms/export.csv")
def export_csv(language: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    rows = session.scalars(
        select(Term).where(Term.user_id == user.id, Term.language == language).order_by(Term.key)).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["term", "kind", "status", "meaning", "context", "notes", "tags"])
    for t in rows:
        writer.writerow([t.key, t.kind, t.status, t.meaning, t.context, t.notes, " ".join(t.tags or [])])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="glosa-{language}.csv"'},
    )


@router.get("/review/queue")
def review_queue(language: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    size = settings_store.get(session, user.id, "review")["session_size"]
    rows = session.scalars(
        select(Term)
        .where(Term.user_id == user.id, Term.language == language, Term.status.in_(LEARNING), Term.srs_due <= _now())
        .order_by(Term.srs_due)
        .limit(size)
    ).all()
    return [term_out(t) for t in rows]


class AnswerIn(BaseModel):
    correct: bool


@router.post("/review/{term_id}/answer")
def review_answer(term_id: int, body: AnswerIn, user: User = Depends(current_user),
                  session: Session = Depends(get_session)):
    term = own_term(session, user.id, term_id)
    now = _now()
    srs.answer(term, body.correct, now)
    session.commit()
    due = term.srs_due is not None and term.srs_due.replace(tzinfo=term.srs_due.tzinfo or timezone.utc) <= now
    return {"term": term_out(term), "still_due": due}
