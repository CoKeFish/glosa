import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.languages import UnsupportedLanguage, get_language
from app.models import Term


def require_language(code: str):
    try:
        return get_language(code)
    except UnsupportedLanguage:
        raise HTTPException(400, f"Idioma no soportado: {code}")


def normalize_key(key: str) -> str:
    return re.sub(r"\s+", " ", key.strip().lower())


def term_out(t: Term) -> dict:
    return {
        "id": t.id,
        "language": t.language,
        "key": t.key,
        "kind": t.kind,
        "status": t.status,
        "meaning": t.meaning,
        "notes": t.notes,
        "tags": t.tags or [],
        "context": t.context,
        "srs_due": t.srs_due.isoformat() if t.srs_due else None,
        "streak": t.streak,
    }


def status_map(session: Session, language: str) -> dict[str, int]:
    rows = session.execute(select(Term.key, Term.status).where(Term.language == language))
    return {key: status for key, status in rows}
