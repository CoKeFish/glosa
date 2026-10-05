import asyncio

import pytest

from app import translation_cache
from app.db import SessionLocal, engine
from app.models import Base, TranslationCache


@pytest.fixture
def session():
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        s.query(TranslationCache).delete()
        s.commit()
        yield s


def test_same_text_is_translated_once(session):
    calls = []

    async def translate():
        calls.append(1)
        return "están fuera"

    for _ in range(3):
        result = asyncio.run(translation_cache.cached(session, "local", "en", "es", "lie outside", translate))
    assert result == "están fuera"
    assert len(calls) == 1


def test_each_translator_has_its_own_entry(session):
    asyncio.run(translation_cache.cached(session, "local", "en", "es", "lie outside", _const("miente afuera")))
    ai = asyncio.run(translation_cache.cached(session, "ai:anthropic:claude-opus-5-5", "en", "es", "lie outside",
                                              _const("quedar fuera")))
    assert ai == "quedar fuera"


def test_many_only_sends_what_is_missing(session):
    asyncio.run(translation_cache.cached(session, "local", "en", "es", "wide", _const("amplio")))
    sent = []

    async def translate_many(texts):
        sent.extend(texts)
        return [t.upper() for t in texts]

    result = asyncio.run(translation_cache.cached_many(session, "local", "en", "es", ["wide", "open"], translate_many))
    assert result == ["amplio", "OPEN"]
    assert sent == ["open"]


def _const(value):
    async def translate():
        return value
    return translate
