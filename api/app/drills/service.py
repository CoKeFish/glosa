"""Drills: rounds of 7 sentences in the reader's language to translate into English, corrected
by the AI, which then move the syllabus and feed the review queue.

The server decides what each round practises (which topics, how many of each); the AI only
writes the sentences and corrects the answers. Prompts are files (prompts/*.md) the reader can
edit, or their own versions saved in their account.
"""

import random
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import settings_store, srs
from app.ai.base import AIError
from app.ai.service import _parse_json, language_name
from app.models import (LEARNING, Book, ErrorTag, Round, RoundItem, Section, SyllabusTopic, Term)

HERE = Path(__file__).parent
BASE_SYLLABUS = HERE / "temario-base.md"
PROMPTS = {"generator": HERE / "prompts" / "generator.md", "corrector": HERE / "prompts" / "corrector.md"}
ROUND_SIZE = 7
MARKERS = {"⬜": "no_visto", "\U0001f7e1": "falla", "\U0001f7e2": "dominado"}  # ⬜ 🟡 🟢


# --- Syllabus ---------------------------------------------------------------------------

def parse_syllabus(markdown: str) -> list[dict]:
    """Topics of a temario.md: "## 2. Presente" opens a block, "- 🟡 …" is a topic."""
    topics, block = [], ""
    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith("## "):
            block = line[3:].strip()
        elif line.startswith("- ") and block:
            text = line[2:].strip()
            status = "no_visto"
            for marker, value in MARKERS.items():
                if text.startswith(marker):
                    status, text = value, text[len(marker):].strip()
                    break
            if text:
                topics.append({"block": block, "description": text, "status": status})
    return topics


def replace_syllabus(session: Session, user_id: int, markdown: str) -> int:
    topics = parse_syllabus(markdown)
    if not topics:
        raise ValueError("No encontré temas: el archivo necesita bloques «## …» y temas «- ⬜ …»")
    session.query(SyllabusTopic).filter(SyllabusTopic.user_id == user_id).delete()
    for position, t in enumerate(topics):
        session.add(SyllabusTopic(user_id=user_id, position=position, **t))
    session.flush()
    _ensure_active(session, user_id)
    session.commit()
    return len(topics)


def syllabus(session: Session, user_id: int) -> list[SyllabusTopic]:
    """The reader's syllabus; the first time, the base template (every topic unseen)."""
    rows = session.scalars(select(SyllabusTopic).where(SyllabusTopic.user_id == user_id)
                           .order_by(SyllabusTopic.position)).all()
    if not rows:
        replace_syllabus(session, user_id, BASE_SYLLABUS.read_text(encoding="utf-8"))
        return syllabus(session, user_id)
    return list(rows)


def _ensure_active(session: Session, user_id: int) -> None:
    """One topic is the one being learned: when none is, the first one not mastered."""
    topics = session.scalars(select(SyllabusTopic).where(SyllabusTopic.user_id == user_id)
                             .order_by(SyllabusTopic.position)).all()
    if any(t.active for t in topics):
        return
    pick = next((t for t in topics if t.status == "no_visto"), None) or next(
        (t for t in topics if t.status == "falla"), None)
    if pick is not None:
        pick.active = True


def set_active(session: Session, user_id: int, topic_id: int) -> None:
    for t in session.scalars(select(SyllabusTopic).where(SyllabusTopic.user_id == user_id)):
        t.active = t.id == topic_id
    session.commit()


# --- Prompts ----------------------------------------------------------------------------

def prompt_text(session: Session, user_id: int, name: str) -> str:
    """The reader's saved version, or the file (read every time, so edits apply at once)."""
    saved = settings_store.get(session, user_id, "drills.prompts").get(name)
    return saved if saved and saved.strip() else PROMPTS[name].read_text(encoding="utf-8")


def _split(template: str, values: dict[str, str]) -> tuple[str, str]:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    if "---SYSTEM---" not in template or "---PROMPT---" not in template:
        raise AIError("El prompt necesita las secciones ---SYSTEM--- y ---PROMPT---")
    _, rest = template.split("---SYSTEM---", 1)
    system, prompt = rest.split("---PROMPT---", 1)
    return system.strip(), prompt.strip()


# --- A new round ------------------------------------------------------------------------

@dataclass
class Slot:
    topics: list[SyllabusTopic]
    kind: str  # falla | activo | repaso


def plan_round(topics: list[SyllabusTopic], rng: random.Random | None = None) -> list[Slot]:
    """2-3 sentences on failing topics (oldest practised first), 2 on the active topic, 2 on
    mastered ones for review; whatever a group lacks is filled from the others."""
    rng = rng or random.Random()
    never = datetime.min.replace(tzinfo=timezone.utc)
    oldest = lambda t: t.last_practiced or never  # noqa: E731
    failing = sorted([t for t in topics if t.status == "falla"], key=oldest)
    mastered = sorted([t for t in topics if t.status == "dominado"], key=oldest)
    active = next((t for t in topics if t.active), None) or next(
        (t for t in topics if t.status == "no_visto"), None)

    slots: list[Slot] = []
    if active is not None:
        slots += [Slot([active], "activo"), Slot([active], "activo")]
    review = mastered[:4]
    rng.shuffle(review)
    slots += [Slot([t], "repaso") for t in review[:2]]
    pool = [t for t in failing if t is not active]
    need = ROUND_SIZE - len(slots)
    for i in range(need):
        if pool:
            # Mixing: the third failing sentence pairs two failing topics when there are many.
            first = pool[i % len(pool)]
            pair = pool[(i + 3) % len(pool)] if len(pool) > 3 and i == 2 else None
            slots.append(Slot([first] + ([pair] if pair and pair is not first else []), "falla"))
        elif mastered:
            slots.append(Slot([mastered[i % len(mastered)]], "repaso"))
        elif active is not None:
            slots.append(Slot([active], "activo"))
    order = {"falla": 0, "activo": 1, "repaso": 2}
    return sorted(slots[:ROUND_SIZE], key=lambda s: order[s.kind])


def book_vocabulary(session: Session, user_id: int, book_id: int | None, limit: int = 15) -> list[str]:
    """Words being learned (statuses 1-3) that appear in the given book."""
    if book_id is None:
        return []
    book = session.get(Book, book_id)
    if book is None or book.user_id != user_id:
        return []
    keys: set[str] = set()
    for tokens in session.scalars(select(Section.tokens).where(Section.book_id == book_id)):
        keys |= {t["k"] for t in tokens if t.get("w")}
    learning = session.scalars(
        select(Term.key).where(Term.user_id == user_id, Term.language == book.language,
                               Term.status.in_(LEARNING[:3]), Term.kind == "word")
        .order_by(Term.updated_at.desc())
    ).all()
    return [k for k in learning if k in keys][:limit]


async def generate(model, session: Session, user_id: int, book_id: int | None) -> Round:
    topics = syllabus(session, user_id)
    slots = plan_round(topics)
    if len(slots) < ROUND_SIZE:
        raise AIError("El temario no tiene temas suficientes para una ronda")
    native = language_name(settings_store.native_language(session, user_id))
    plan = "\n".join(
        f"{i}. ({s.kind}) " + "; ".join(f"[{t.id}] {t.block} — {t.description}" for t in s.topics)
        for i, s in enumerate(slots, 1)
    )
    book = session.get(Book, book_id) if book_id is not None else None
    if book is not None and book.user_id != user_id:
        book = None
    vocabulary = ", ".join(book_vocabulary(session, user_id, book.id if book else None)) or "(none)"
    system, prompt = _split(prompt_text(session, user_id, "generator"),
                            {"native": native, "plan": plan, "vocabulary": vocabulary})
    data = _parse_json(await model.complete(system, prompt, max_tokens=2000))
    by_slot = {int(i.get("slot", 0)): str(i.get("spanish", "")).strip() for i in data.get("items", [])
               if isinstance(i, dict)}
    sentences = [by_slot.get(n) or "" for n in range(1, ROUND_SIZE + 1)]
    if not all(sentences):
        # The model numbered them its own way: take them in order.
        listed = [str(i.get("spanish", "")).strip() for i in data.get("items", []) if isinstance(i, dict)]
        sentences = (listed + [""] * ROUND_SIZE)[:ROUND_SIZE]
    if not all(sentences):
        raise AIError("La IA no devolvió las 7 oraciones")
    round_ = Round(user_id=user_id, book_id=book.id if book else None)
    for position, (slot, spanish) in enumerate(zip(slots, sentences)):
        round_.items.append(RoundItem(position=position, spanish=spanish, topic_ids=[t.id for t in slot.topics]))
    session.add(round_)
    session.commit()
    return round_


# --- Correction ---------------------------------------------------------------------------

def normalize_tag(tag: str) -> str:
    """"Tercera persona -s" → "tercera_persona_s": lower case, ASCII, words joined by _."""
    ascii_tag = unicodedata.normalize("NFKD", tag).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_tag.lower()).strip("_")[:80]


async def correct(model, session: Session, user_id: int, round_: Round, answers: list[str]) -> Round:
    if round_.corrected_at is not None:
        raise AIError("Esta ronda ya está corregida")
    if len(answers) != len(round_.items):
        raise AIError(f"Hacen falta {len(round_.items)} respuestas")
    topics = {t.id: t for t in syllabus(session, user_id)}
    for item, answer in zip(round_.items, answers):
        item.answer = answer.strip()
    native = language_name(settings_store.native_language(session, user_id))
    listing = "\n".join(
        f"{i}. {native}: {item.spanish}\n   Topics: "
        + "; ".join(f"[{tid}] {topics[tid].description}" for tid in item.topic_ids if tid in topics)
        + f"\n   Learner's English: {item.answer or '(left blank)'}"
        for i, item in enumerate(round_.items, 1)
    )
    known = ", ".join(session.scalars(select(ErrorTag.tag).order_by(ErrorTag.tag))) or "(none yet)"
    system, prompt = _split(prompt_text(session, user_id, "corrector"),
                            {"native": native, "items": listing, "known_tags": known})
    data = _parse_json(await model.complete(system, prompt, max_tokens=8000))
    results = {int(r.get("n", 0)): r for r in data.get("items", []) if isinstance(r, dict)}
    if len(results) < len(round_.items):
        raise AIError("La IA no corrigió todas las oraciones; prueba otra vez")

    for n, item in enumerate(round_.items, 1):
        r = results.get(n, {})
        item.verdict = "correcta" if str(r.get("verdict", "")).startswith("correct") else "con_errores"
        item.correction = str(r.get("correction") or item.answer).strip()
        item.explanation = str(r.get("explanation", "")).strip()
        item.examples = [str(e).strip() for e in (r.get("examples") or []) if str(e).strip()][:3]
        item.failed_topic_ids = [int(t) for t in (r.get("failed_topics") or [])
                                 if str(t).isdigit() and int(t) in item.topic_ids]
        item.error_tags = [_tag(session, t) for t in dict.fromkeys(
            normalize_tag(str(t)) for t in (r.get("error_tags") or [])) if t]
        if item.verdict == "correcta":
            item.error_tags, item.failed_topic_ids = [], []
    round_.closing_note = str(data.get("closing_note", "")).strip()
    round_.corrected_at = datetime.now(timezone.utc)
    update_syllabus(round_, topics, round_.corrected_at)
    _to_review(session, user_id, data)
    session.commit()
    return round_


def _tag(session: Session, tag: str) -> ErrorTag:
    row = session.scalar(select(ErrorTag).where(ErrorTag.tag == tag))
    if row is None:
        row = ErrorTag(tag=tag)
        session.add(row)
        session.flush()
    return row


def update_syllabus(round_: Round, topics: dict[int, SyllabusTopic], when: datetime) -> None:
    """falla → dominado after two rounds in a row without an error on the topic; dominado →
    falla as soon as an error on it comes back. An unseen topic becomes falla on its first
    error, and dominado after two clean rounds like any other."""
    practised = {tid for item in round_.items for tid in item.topic_ids if tid in topics}
    failed = {tid for item in round_.items for tid in item.failed_topic_ids}
    for tid in practised:
        topic = topics[tid]
        topic.last_practiced = when
        if tid in failed:
            topic.status, topic.streak = "falla", 0
        else:
            topic.streak += 1
            if topic.streak >= 2:
                topic.status = "dominado"


def _to_review(session: Session, user_id: int, data: dict) -> None:
    """Rules and new vocabulary join the spaced review queue, as terms of the studied language."""
    now = datetime.now(timezone.utc)

    def add(key: str, kind: str, meaning: str, context: str) -> None:
        key = re.sub(r"\s+", " ", key.strip().lower())[:300]
        if not key:
            return
        term = session.scalar(select(Term).where(Term.user_id == user_id, Term.language == "en", Term.key == key))
        if term is None:
            term = Term(user_id=user_id, language="en", key=key, kind=kind, meaning="", notes="", tags=["drills"],
                        context="")
            srs.set_status(term, 1, now)
            session.add(term)
        elif term.status not in LEARNING:
            srs.set_status(term, 1, now)  # known or ignored before, missed now: back to learning
        term.meaning = term.meaning or meaning
        term.context = term.context or context

    for rule in (data.get("rules") or [])[:5]:
        if isinstance(rule, dict) and rule.get("rule"):
            add(str(rule["rule"]), "rule", str(rule.get("example", "")), str(rule.get("example", "")))
    for word in (data.get("vocabulary") or [])[:8]:
        if isinstance(word, dict) and word.get("en"):
            kind = "word" if " " not in str(word["en"]).strip() else "phrase"
            add(str(word["en"]), kind, str(word.get("es", "")), "")


# --- Statistics -------------------------------------------------------------------------

def error_stats(session: Session, user_id: int) -> list[dict]:
    from app.models import RoundItemError

    rows = session.execute(
        select(ErrorTag.tag, func.count())
        .join(RoundItemError, RoundItemError.tag_id == ErrorTag.id)
        .join(RoundItem, RoundItem.id == RoundItemError.item_id)
        .join(Round, Round.id == RoundItem.round_id)
        .where(Round.user_id == user_id)
        .group_by(ErrorTag.tag)
        .order_by(func.count().desc())
    ).all()
    return [{"tag": tag, "count": n} for tag, n in rows]
