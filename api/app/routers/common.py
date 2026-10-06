import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.languages import UnsupportedLanguage, get_language
from app.models import Book, Section, Term


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


def status_map(session: Session, user_id: int, language: str) -> dict[str, int]:
    rows = session.execute(select(Term.key, Term.status).where(Term.user_id == user_id, Term.language == language))
    return {key: status for key, status in rows}


# Someone else's book, section or term answers 404, exactly like one that does not exist.

def own_book(session: Session, user_id: int, book_id: int) -> Book:
    book = session.get(Book, book_id)
    if book is None or book.user_id != user_id:
        raise HTTPException(404, "Libro no encontrado")
    return book


def own_section(session: Session, user_id: int, section_id: int) -> Section:
    section = session.get(Section, section_id)
    if section is None or section.book.user_id != user_id:
        raise HTTPException(404, "Sección no encontrada")
    return section


def own_term(session: Session, user_id: int, term_id: int) -> Term:
    term = session.get(Term, term_id)
    if term is None or term.user_id != user_id:
        raise HTTPException(404, "Término no encontrado")
    return term
