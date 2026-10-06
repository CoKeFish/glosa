from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import importers, settings_store
from app.auth import current_user
from app.db import get_session
from app.models import KNOWN, Book, Section, Term, User
from app.routers.common import own_book, own_section, require_language, status_map, term_out

router = APIRouter(prefix="/api")


def _new_ratio(tokens: list[dict], statuses: dict[str, int]) -> tuple[int, int]:
    keys = {t["k"] for t in tokens if t["w"]}
    new = sum(1 for k in keys if k not in statuses)
    return new, len(keys)


@router.get("/books")
def list_books(user: User = Depends(current_user), session: Session = Depends(get_session)):
    counts = {
        book_id: (n, words)
        for book_id, n, words in session.execute(
            select(Section.book_id, func.count(), func.sum(Section.word_count))
            .join(Book).where(Book.user_id == user.id).group_by(Section.book_id)
        )
    }
    books = session.scalars(select(Book).where(Book.user_id == user.id).order_by(Book.created_at.desc())).all()
    return [
        {"id": b.id, "title": b.title, "language": b.language, "sections": counts.get(b.id, (0, 0))[0],
         "words": int(counts.get(b.id, (0, 0))[1] or 0), "current_position": b.current_position}
        for b in books
    ]


@router.post("/books/import")
async def import_book(
    language: str = Form(...),
    title: str = Form(""),
    text: str = Form(""),
    file: UploadFile | None = None,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    pack = require_language(language)
    try:
        if file is not None and file.filename:
            detected_title, raw = importers.from_upload(file.filename, await file.read())
        else:
            detected_title, raw = None, importers.from_text(title or "Sin título", text)
    except importers.ImportError_ as exc:
        raise HTTPException(400, str(exc))

    # spaCy is CPU-bound; keep it off the event loop.
    analyses = await run_in_threadpool(lambda: [pack.analyze(s.text) for s in raw])
    book = Book(user_id=user.id, title=title.strip() or detected_title or "Sin título", language=language)
    for position, (section, analysis) in enumerate(zip(raw, analyses)):
        book.sections.append(
            Section(position=position, title=section.title, text=section.text, tokens=analysis.tokens,
                    units=analysis.units, grammar=analysis.grammar, word_count=analysis.word_count)
        )
    session.add(book)
    session.commit()
    return {"id": book.id, "sections": len(raw)}


@router.get("/books/{book_id}")
def get_book(book_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    book = own_book(session, user.id, book_id)
    statuses = status_map(session, user.id, book.language)
    sections = []
    for s in book.sections:
        new, unique = _new_ratio(s.tokens, statuses)
        sections.append({"id": s.id, "position": s.position, "title": s.title, "word_count": s.word_count,
                         "new_words": new, "new_pct": round(100 * new / unique) if unique else 0})
    return {"id": book.id, "title": book.title, "language": book.language,
            "current_position": book.current_position, "sections": sections}


@router.post("/books/{book_id}/reanalyze")
async def reanalyze_book(book_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Run the language pack again over a book, after its rules have improved. Vocabulary is untouched."""
    book = own_book(session, user.id, book_id)
    pack = require_language(book.language)
    texts = [s.text for s in book.sections]
    analyses = await run_in_threadpool(lambda: [pack.analyze(t) for t in texts])
    for section, analysis in zip(book.sections, analyses):
        section.tokens, section.units, section.grammar = analysis.tokens, analysis.units, analysis.grammar
        section.word_count = analysis.word_count
    session.commit()
    return {"sections": len(analyses)}


@router.delete("/books/{book_id}")
def delete_book(book_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    book = own_book(session, user.id, book_id)
    session.delete(book)
    session.commit()
    return {"ok": True}


POSSESSIVES = {"my", "your", "his", "her", "its", "our", "their"}


def _part_matches(token: dict, part: str) -> bool:
    if part in ("one's", "someone's", "somebody's"):
        return token["k"] in POSSESSIVES
    return token["k"] == part or token.get("l") == part


def _phrase_units(tokens: list[dict], saved: list[tuple[str, str]]) -> list[dict]:
    """Find saved multi-word terms in the section (phrases the reader saved, expressions the AI
    found). Words match by form or base form, so "make up one's mind" also finds "made up her
    mind"; punctuation between words is skipped."""
    words = [(i, t) for i, t in enumerate(tokens) if t["w"]]
    units = []
    for key, kind in saved:
        parts = key.split(" ")
        n = len(parts)
        for start in range(len(words) - n + 1):
            if all(_part_matches(words[start + j][1], parts[j]) for j in range(n)):
                first, last = words[start][0], words[start + n - 1][0]
                units.append({"k": key, "kind": kind, "i": list(range(first, last + 1)), "sep": False})
    return units


def _structure_lemma(tokens: list[dict], indices: list[int], language: str) -> str | None:
    """Base form of the structure's main verb ("led" → "lead"), only when it is a real word:
    the parser guesses lemmas for rare words ("inurned" → "inurne")."""
    from wordfreq import zipf_frequency

    last = next((tokens[i] for i in reversed(indices) if tokens[i]["w"]), None)
    if not last or not last.get("l") or last["l"] == last["k"]:
        return None
    return last["l"] if zipf_frequency(last["l"], language) > 0 else None


@router.get("/sections/{section_id}")
def get_section(section_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    section = own_section(session, user.id, section_id)
    book = section.book
    pack = require_language(book.language)

    saved = session.execute(
        select(Term.key, Term.kind).where(Term.user_id == user.id, Term.language == book.language,
                                         Term.kind.in_(("phrase", "expression")))
    ).all()
    detected = {(u["k"], tuple(u["i"])) for u in section.units}
    extra = [u for u in _phrase_units(section.tokens, [tuple(r) for r in saved])
             if (u["k"], tuple(u["i"])) not in detected]
    units = section.units + extra

    keys = {t["k"] for t in section.tokens if t["w"]} | {u["k"] for u in units}
    terms = session.scalars(
        select(Term).where(Term.user_id == user.id, Term.language == book.language, Term.key.in_(keys))
    ).all()

    neighbours = {s.position: s.id for s in book.sections}
    grammar_types = pack.grammar_types(settings_store.native_language(session, user.id))
    return {
        "id": section.id,
        "title": section.title,
        "position": section.position,
        "book": {"id": book.id, "title": book.title, "language": book.language, "sections": len(neighbours)},
        "prev_id": neighbours.get(section.position - 1),
        "next_id": neighbours.get(section.position + 1),
        "tokens": section.tokens,
        "units": units,
        "grammar": [
            {**g, "label": grammar_types[g["type"]].label, "explanation": grammar_types[g["type"]].explanation,
             "lemma": _structure_lemma(section.tokens, g["i"], book.language)}
            for g in section.grammar or [] if g["type"] in grammar_types
        ],
        "terms": {t.key: term_out(t) for t in terms},
    }


class Position(BaseModel):
    position: int


@router.post("/books/{book_id}/position")
def set_position(book_id: int, body: Position, user: User = Depends(current_user),
                 session: Session = Depends(get_session)):
    book = own_book(session, user.id, book_id)
    book.current_position = body.position
    session.commit()
    return {"ok": True}


@router.get("/stats")
def stats(language: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    statuses = status_map(session, user.id, language)
    return {
        # Like LingQ: known words count terms marked known plus those at status 4.
        "known_words": sum(1 for s in statuses.values() if s in (4, KNOWN)),
        "learning": sum(1 for s in statuses.values() if 1 <= s <= 3),
        "total_saved": sum(1 for s in statuses.values() if 1 <= s <= 4),
    }
