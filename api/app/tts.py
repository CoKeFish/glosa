"""Local text-to-speech engines behind one interface.

Each engine runs in its own container (see compose.yaml) and speaks the OpenAI audio API
(POST /v1/audio/speech). Kokoro is the main voice; Supertonic covers the languages Kokoro
lacks. The browser's own voice is the last fallback, in the web app.
"""

import os
from dataclasses import dataclass

import httpx


class TTSError(Exception):
    pass


@dataclass(frozen=True)
class Engine:
    id: str
    label: str
    url: str
    languages: frozenset[str]  # languages it can speak
    default_voices: dict[str, str]  # language → voice used when the reader has not chosen one


# Kokoro names voices by a language letter: a/b English (US/UK), e Spanish, f French, …
KOKORO_PREFIX = {"en": ("a", "b"), "es": ("e",), "fr": ("f",), "it": ("i",), "pt": ("p",), "ja": ("j",),
                 "zh": ("z",), "hi": ("h",)}
KOKORO_ACCENT = {"a": "EE. UU.", "b": "Reino Unido"}
SUPERTONIC_LANGUAGES = frozenset({
    "en", "es", "fr", "de", "it", "pt", "nl", "ru", "pl", "uk", "cs", "sv", "da", "no", "fi", "el", "tr", "ar",
    "he", "hi", "ja", "ko", "zh", "vi", "th", "id", "ms", "ro", "hu", "bg", "hr",
})

KOKORO = Engine("kokoro", "Kokoro", os.environ.get("TTS_KOKORO_URL", "http://tts-kokoro:8880"),
                frozenset(KOKORO_PREFIX),
                {"en": "af_heart", "es": "ef_dora", "fr": "ff_siwis", "it": "if_sara", "pt": "pf_dora"})
SUPERTONIC = Engine("supertonic", "Supertonic 3", os.environ.get("TTS_SUPERTONIC_URL", "http://tts-supertonic:7788"),
                    SUPERTONIC_LANGUAGES, {})  # same voices for every language
ENGINES = {e.id: e for e in (KOKORO, SUPERTONIC)}


def engine_for(engine_id: str, language: str) -> str:
    """The chosen engine if it speaks the language, otherwise one that does (Kokoro → Supertonic)."""
    if engine_id in ENGINES and language in ENGINES[engine_id].languages:
        return engine_id
    return next((e.id for e in ENGINES.values() if language in e.languages), engine_id)


async def voices(engine_id: str, language: str) -> list[dict]:
    """Voices of the engine for `language`, best first, as {"id", "label"}."""
    engine = ENGINES[engine_id]
    if language not in engine.languages:
        return []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if engine_id == "kokoro":
                data = (await client.get(f"{engine.url}/v1/audio/voices")).json()["voices"]
                prefixes = KOKORO_PREFIX[language]
                grade = lambda v: v.get("overall_grade") or "Z"  # noqa: E731  ungraded voices last
                items = [v for v in data if v["id"][:1] in prefixes and "_v0" not in v["id"]]
                items.sort(key=grade)
                return [{"id": v["id"], "label": _kokoro_label(v)} for v in items]
            data = (await client.get(f"{engine.url}/v1/styles")).json()["styles"]
            return [{"id": s["name"], "label": ("Mujer " if s["name"].startswith("F") else "Hombre ") + s["name"][1:]}
                    for s in data]
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise TTSError(f"{engine.label} no responde") from exc


def _kokoro_label(v: dict) -> str:
    name = v["id"].split("_", 1)[1].replace("_", " ").title()
    gender = "mujer" if v["id"][1] == "f" else "hombre"
    accent = KOKORO_ACCENT.get(v["id"][0])
    parts = [gender] + ([accent] if accent else []) + ([f"calidad {v['overall_grade']}"] if v.get("overall_grade") else [])
    return f"{name} ({', '.join(parts)})"


def default_voice(engine_id: str, language: str) -> str:
    return ENGINES[engine_id].default_voices.get(language, "F1" if engine_id == "supertonic" else "")


async def synthesize(engine_id: str, voice: str, text: str, language: str) -> tuple[bytes, str]:
    """Audio bytes and their media type."""
    engine = ENGINES[engine_id]
    voice = voice or default_voice(engine_id, language)
    if engine_id == "kokoro":
        body, media = {"model": "kokoro", "input": text, "voice": voice, "response_format": "mp3"}, "audio/mpeg"
    else:  # Supertonic has no MP3
        body = {"model": "supertonic-3", "input": text, "voice": voice, "lang": language, "response_format": "ogg"}
        media = "audio/ogg"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{engine.url}/v1/audio/speech", json=body)
    except httpx.HTTPError as exc:
        raise TTSError(f"{engine.label} no responde") from exc
    if resp.status_code != 200:
        raise TTSError(f"{engine.label} respondió {resp.status_code}: {resp.text[:200]}")
    return resp.content, media
