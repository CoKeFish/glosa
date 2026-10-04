"""Wiktionary data as extracted by Kaikki (https://kaikki.org), one JSON line per entry.

Unlike Wiktionary's own definition API, it includes the translation tables, so a word
comes with short equivalents in the reader's language ("turn off" → "apagar") instead of
only English definitions. Data is CC BY-SA, from Wiktionary.
"""

import json
from urllib.parse import quote

import httpx

from app.dictionary.base import DictionaryEntry, DictionaryError, Translation

BASE = "https://kaikki.org/dictionary/{language}/meaning/{a}/{ab}/{word}.jsonl"
USER_AGENT = "glosa/0.1 (open source language reader)"
MAX_DEFINITIONS = 6
SKIP_FORM_TAGS = {"table-tags", "inflection-template", "class"}


def _url(language_name: str, word: str) -> str:
    return BASE.format(language=language_name, a=quote(word[:1]), ab=quote(word[:2]), word=quote(word))


def _match_sense(translation_sense: str, senses: list[dict]) -> dict | None:
    """Translation tables name their sense with a short summary of one of the glosses."""
    needle = translation_sense.lower().removeprefix("intransitive:").removeprefix("transitive:").strip()
    if not needle:
        return None
    for sense in senses:
        gloss = " ".join(sense.get("glosses") or []).lower()
        if needle[:40] in gloss:
            return sense
    return None


def parse_lines(lines: list[dict], meaning_language: str) -> list[DictionaryEntry]:
    entries = []
    for d in lines:
        senses = d.get("senses", [])
        definitions, examples, form_of = [], [], []
        for sense in senses:
            gloss = (sense.get("glosses") or [""])[-1].strip()
            if gloss and gloss not in definitions:
                definitions.append(gloss)
            examples.extend(e["text"] for e in sense.get("examples", [])[:1] if e.get("text"))
            form_of.extend(f["word"] for f in sense.get("form_of", []) if f.get("word"))
        translations, seen = [], set()
        for t in d.get("translations", []):
            if t.get("lang_code") != meaning_language or not t.get("word") or t["word"] in seen:
                continue
            seen.add(t["word"])
            sense = _match_sense(t.get("sense", ""), senses) or {}
            example = next((e.get("text", "") for e in sense.get("examples", []) if e.get("text")), "")
            translations.append(
                Translation(
                    text=t["word"],
                    sense=t.get("sense", ""),
                    tags=sense.get("tags", []),
                    gloss=(sense.get("glosses") or [""])[-1],
                    example=example,
                )
            )
        forms = [
            f["form"] for f in d.get("forms", [])
            if f.get("form") and not SKIP_FORM_TAGS & set(f.get("tags", []))
        ]
        ipa, audio = _sounds(d.get("sounds", []))
        if definitions or translations:
            entries.append(
                DictionaryEntry(
                    part_of_speech=d.get("pos", ""),
                    definitions=definitions[:MAX_DEFINITIONS],
                    examples=examples[:2],
                    translations=translations,
                    form_of=list(dict.fromkeys(form_of)),
                    word=d.get("word", ""),
                    forms=list(dict.fromkeys(forms)),
                    ipa=ipa,
                    audio=audio,
                    etymology=d.get("etymology_number", 0) or 0,
                )
            )
    return entries


US_TAGS = {"US", "General-American"}
UK_TAGS = {"UK", "Received-Pronunciation", "Southern-England"}


def _accent(tags: list[str]) -> str:
    if US_TAGS & set(tags):
        return "US"
    if UK_TAGS & set(tags):
        return "UK"
    return tags[0] if tags else ""


def _sounds(sounds: list[dict]) -> tuple[list[str], list[dict]]:
    """IPA transcriptions and recorded audio (Wikimedia Commons), American first."""
    ipa = list(dict.fromkeys(s["ipa"] for s in sounds if s.get("ipa", "").startswith("/")))
    audio = [
        {"url": s.get("mp3_url") or s["ogg_url"], "accent": _accent(s.get("tags", []))}
        for s in sounds if s.get("mp3_url") or s.get("ogg_url")
    ]
    audio.sort(key=lambda a: {"US": 0, "UK": 1}.get(a["accent"], 2))
    return ipa[:2], audio[:3]


class KaikkiDictionary:
    name = "Wiktionary"

    def __init__(self, language_code: str, language_name: str):
        # Bump the version suffix when the cached shape changes.
        self.id = f"kaikki4-{language_code}"
        self.language_name = language_name

    async def lookup(self, term: str, meaning_language: str) -> list[DictionaryEntry]:
        word = term.strip()
        try:
            async with httpx.AsyncClient(timeout=15, headers={"User-Agent": USER_AGENT}) as client:
                resp = await client.get(_url(self.language_name, word))
        except httpx.HTTPError as exc:
            raise DictionaryError(f"Wiktionary (Kaikki) no responde: {exc}") from exc
        if resp.status_code == 404:
            return []
        if resp.status_code != 200:
            raise DictionaryError(f"Wiktionary (Kaikki) devolvió {resp.status_code}")
        lines = [json.loads(line) for line in resp.text.splitlines() if line.strip()]
        return parse_lines(lines, meaning_language)
