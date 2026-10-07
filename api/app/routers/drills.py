"""Drills: guided translation practice. Every route belongs to the signed-in reader."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import settings_store
from app.ai.base import AINotConfigured
from app.ai.registry import build_text_model
from app.auth import current_user
from app.db import get_session
from app.drills import service
from app.keystore import stored_key
from app.models import TOPIC_STATUSES, Round, SyllabusTopic, User
from app.routers.assist import _model, _run

router = APIRouter(prefix="/api/drills", dependencies=[Depends(current_user)])


def _topic_out(t: SyllabusTopic) -> dict:
    return {"id": t.id, "block": t.block, "description": t.description, "status": t.status, "active": t.active,
            "streak": t.streak, "last_practiced": t.last_practiced.isoformat() if t.last_practiced else None}


def _round_out(r: Round, full: bool = True) -> dict:
    items = r.items
    out = {"id": r.id, "created_at": r.created_at.isoformat() if r.created_at else None,
           "corrected_at": r.corrected_at.isoformat() if r.corrected_at else None, "book_id": r.book_id,
           "closing_note": r.closing_note,
           "correct": sum(1 for i in items if i.verdict == "correcta"), "total": len(items)}
    if full:
        out["items"] = [{"id": i.id, "spanish": i.spanish, "topic_ids": i.topic_ids, "answer": i.answer,
                         "correction": i.correction, "explanation": i.explanation, "examples": i.examples,
                         "failed_topic_ids": i.failed_topic_ids, "verdict": i.verdict,
                         "error_tags": [t.tag for t in i.error_tags]} for i in items]
    return out


def _own_round(session: Session, user: User, round_id: int) -> Round:
    round_ = session.get(Round, round_id)
    if round_ is None or round_.user_id != user.id:
        raise HTTPException(404, "Ronda no encontrada")
    return round_


@router.get("/status")
def status(user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Whether drills can run: they need a configured AI; nothing is corrected by local rules."""
    config = settings_store.text_model_config(session, user.id)
    try:
        build_text_model(config, lambda p: stored_key(session, user.id, p))
        return {"ready": True, "provider": config.provider, "model": config.model, "reason": None}
    except AINotConfigured as exc:
        return {"ready": False, "provider": config.provider, "model": config.model, "reason": str(exc)}


@router.get("/syllabus")
def get_syllabus(user: User = Depends(current_user), session: Session = Depends(get_session)):
    return [_topic_out(t) for t in service.syllabus(session, user.id)]


class TopicPatch(BaseModel):
    status: str | None = None
    active: bool | None = None


@router.patch("/syllabus/{topic_id}")
def patch_topic(topic_id: int, body: TopicPatch, user: User = Depends(current_user),
                session: Session = Depends(get_session)):
    topic = session.get(SyllabusTopic, topic_id)
    if topic is None or topic.user_id != user.id:
        raise HTTPException(404, "Tema no encontrado")
    if body.status is not None:
        if body.status not in TOPIC_STATUSES:
            raise HTTPException(400, f"Estado inválido: {body.status}")
        topic.status, topic.streak = body.status, 0
    if body.active:
        service.set_active(session, user.id, topic.id)
    session.commit()
    return _topic_out(topic)


@router.post("/syllabus/import")
async def import_syllabus(file: UploadFile, user: User = Depends(current_user),
                          session: Session = Depends(get_session)):
    """Replace the syllabus with a temario.md (blocks "## …", topics "- ⬜/🟡/🟢 …")."""
    try:
        count = service.replace_syllabus(session, user.id, (await file.read()).decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(400, str(exc))
    return {"topics": count}


@router.get("/rounds")
def list_rounds(user: User = Depends(current_user), session: Session = Depends(get_session)):
    rounds = session.scalars(select(Round).where(Round.user_id == user.id).order_by(Round.created_at.desc())).all()
    return [_round_out(r, full=False) for r in rounds]


class NewRound(BaseModel):
    book_id: int | None = None


@router.post("/rounds")
async def new_round(body: NewRound, user: User = Depends(current_user), session: Session = Depends(get_session)):
    model = _model(session, user.id)
    round_ = await _run(service.generate(model, session, user.id, body.book_id), session, model,
                        "drills_generate", user.id)
    return _round_out(round_)


@router.get("/rounds/{round_id}")
def get_round(round_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    return _round_out(_own_round(session, user, round_id))


@router.delete("/rounds/{round_id}")
def delete_round(round_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    session.delete(_own_round(session, user, round_id))
    session.commit()
    return {"ok": True}


class Answers(BaseModel):
    answers: list[str]


@router.post("/rounds/{round_id}/answers")
async def submit(round_id: int, body: Answers, user: User = Depends(current_user),
                 session: Session = Depends(get_session)):
    round_ = _own_round(session, user, round_id)
    model = _model(session, user.id)
    try:
        await _run(service.correct(model, session, user.id, round_, body.answers), session, model,
                   "drills_correct", user.id)
    except HTTPException:
        session.rollback()
        raise
    return _round_out(round_)


@router.get("/stats")
def stats(user: User = Depends(current_user), session: Session = Depends(get_session)):
    return {"errors": service.error_stats(session, user.id)}


@router.get("/prompts")
def get_prompts(user: User = Depends(current_user), session: Session = Depends(get_session)):
    saved = settings_store.get(session, user.id, "drills.prompts")
    return {name: {"text": service.prompt_text(session, user.id, name), "custom": bool(saved.get(name)),
                   "file": f"api/app/drills/prompts/{name}.md"} for name in service.PROMPTS}


class PromptIn(BaseModel):
    text: str  # empty: go back to the file


@router.put("/prompts/{name}")
def put_prompt(name: str, body: PromptIn, user: User = Depends(current_user),
               session: Session = Depends(get_session)):
    if name not in service.PROMPTS:
        raise HTTPException(404, "Prompt desconocido")
    text = body.text.strip()
    if text and ("---SYSTEM---" not in text or "---PROMPT---" not in text):
        raise HTTPException(400, "El prompt necesita las secciones ---SYSTEM--- y ---PROMPT---")
    saved = dict(settings_store.get(session, user.id, "drills.prompts"))
    saved[name] = text
    settings_store.put(session, user.id, "drills.prompts", saved)
    return {"ok": True}

