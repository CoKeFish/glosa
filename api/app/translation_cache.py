"""Translations kept in the database: the same text with the same translator is translated
once. Matters most for the AI, where every call costs money, but the local translator and
the dictionary's ranking (which translates every sentence clicked) use it too."""

import hashlib
from collections.abc import Awaitable, Callable

from sqlalchemy.orm import Session

from app.models import TranslationCache


def translator_id(translator) -> str:
    """"local" for the machine translator; the model too for the others, since another model
    may translate differently."""
    if translator.id == "llm":
        return f"llm:{translator.model}"
    if translator.id == "ai":
        return f"ai:{getattr(translator.model, 'provider_id', '')}:{translator.model.model}"
    return translator.id


def cache_text(text: str, context: str, translator) -> str:
    """What the cache is keyed on: the text, plus its sentence for translators that read it
    (the same fragment can mean different things in different sentences)."""
    return f"{text}\n\n{context}" if translator.uses_context and context and context != text else text


def _key(translator: str, source: str, target: str, text: str) -> str:
    return hashlib.sha256(f"{translator}|{source}|{target}|{text}".encode()).hexdigest()


def get(session: Session, translator: str, source: str, target: str, text: str) -> str | None:
    row = session.get(TranslationCache, _key(translator, source, target, text))
    return row.text if row else None


def put(session: Session, translator: str, source: str, target: str, text: str, translation: str) -> None:
    session.merge(TranslationCache(key=_key(translator, source, target, text), translator=translator,
                                   text=translation))
    session.commit()


async def cached(session: Session, translator: str, source: str, target: str, text: str,
                 translate: Callable[[], Awaitable[str]]) -> str:
    """The stored translation, or `translate()` stored for next time."""
    hit = get(session, translator, source, target, text)
    if hit is not None:
        return hit
    result = await translate()
    put(session, translator, source, target, text, result)
    return result


async def cached_many(session: Session, translator: str, source: str, target: str, texts: list[str],
                      translate_many: Callable[[list[str]], Awaitable[list[str]]]) -> list[str]:
    """Like `cached`, for a list: only the texts never translated go to the translator."""
    found = {t: get(session, translator, source, target, t) for t in texts}
    missing = [t for t in dict.fromkeys(texts) if found[t] is None]
    if missing:
        for text, result in zip(missing, await translate_many(missing)):
            found[text] = result
            session.merge(TranslationCache(key=_key(translator, source, target, text), translator=translator,
                                           text=result))
        session.commit()
    return [found[t] for t in texts]
