"""Wiktionary data as extracted by Kaikki (https://kaikki.org), one JSON line per entry.

Unlike Wiktionary's own definition API, it includes the translation tables, so a word
comes with short equivalents in the reader's language ("turn off" → "apagar") instead of
only English definitions. Data is CC BY-SA, from Wiktionary.
"""

import json
import re
from urllib.parse import quote

import httpx

from app.dictionary.base import DictionaryEntry, DictionaryError, Translation

BASE = "https://kaikki.org/dictionary/{language}/meaning/{a}/{ab}/{word}.jsonl"
USER_AGENT = "glosa/0.1 (open source language reader)"
MAX_DEFINITIONS = 6
SKIP_FORM_TAGS = {"table-tags", "inflection-template", "class"}
REFERENCE = re.compile(r"^(alternative (form |spelling )?(of|to)|synonym of|archaic (form|spelling) of|"
                       r"obsolete (form|spelling) of|short for|clipping of|abbreviation of|contraction of)\b", re.I)


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
        definitions, examples, form_of, see = [], [], [], []
        for sense in senses:
            gloss = (sense.get("glosses") or [""])[-1].strip()
            if gloss and gloss not in definitions:
                definitions.append(gloss)
            examples.extend(e["text"] for e in sense.get("examples", [])[:1] if e.get("text"))
            form_of.extend(f["word"] for f in sense.get("form_of", []) if f.get("word"))
            see.extend(f["word"] for f in sense.get("alt_of", []) if f.get("word"))
            # "alternative to on in most…" (upon), "synonym of …": the meaning lives in the
            # linked word, usually the first link of the gloss.
            if REFERENCE.match(gloss) and sense.get("links"):
                see.append(sense["links"][0][0])
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
                    see=[w for w in dict.fromkeys(see) if w.lower() != d.get("word", "").lower()],
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


async def _fetch(url: str) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": USER_AGENT}) as client:
            resp = await client.get(url)
    except httpx.HTTPError as exc:
        raise DictionaryError(f"Wiktionary (Kaikki) no responde: {exc}") from exc
    if resp.status_code == 404:
        return []
    if resp.status_code != 200:
        raise DictionaryError(f"Wiktionary (Kaikki) devolvió {resp.status_code}")
    return [json.loads(line) for line in resp.text.splitlines() if line.strip()]


class KaikkiDictionary:
    name = "Wiktionary"

    def __init__(self, language_code: str, language_name: str):
        # Bump the version suffix when the cached shape changes.
        self.id = f"kaikki5-{language_code}"
        self.language_name = language_name

    async def lookup(self, term: str, meaning_language: str) -> list[DictionaryEntry]:
        return parse_lines(await _fetch(_url(self.language_name, term.strip())), meaning_language)


# Wiktionary editions written in the reader's meaning language, as Kaikki extracts them:
# meaning language → (edition, name of each studied language in that edition).
EDITIONS = {
    "es": ("eswiktionary", {"en": "Inglés"}),
    "fr": ("frwiktionary", {"en": "Anglais"}),
    "pt": ("ptwiktionary", {"en": "Inglês"}),
    "it": ("itwiktionary", {"en": "Inglese"}),
}
NATIVE_BASE = "https://kaikki.org/{edition}/{language}/meaning/{a}/{ab}/{word}.jsonl"
# Glosses that only name a grammatical form ("Pasado simple del verbo (to) lead."): the
# English edition already follows those to the base word.
FORM_GLOSS = re.compile(r"^(pasado|participio|gerundio|plural|forma|tercera persona|comparativo|superlativo|"
                        r"passé|pluriel|forme|participe|passato|plurale|particípio|forma)\b", re.I)
MAX_PIECE_WORDS = 4


def _gloss_pieces(gloss: str) -> list[str]:
    """ "Yacer, estar acostado, estar tumbado." → three meanings; a gloss that is a sentence
    ("Contracción de going y to, «ir a»") stays whole."""
    gloss = gloss.strip().rstrip(".").strip()
    parts = [p.strip() for p in re.split(r"[,;]\s*", gloss) if p.strip()]
    if len(parts) > 1 and all(len(p.split()) <= MAX_PIECE_WORDS for p in parts):
        return parts
    return [gloss]


def parse_native_lines(lines: list[dict]) -> list[DictionaryEntry]:
    """Entries from a Wiktionary written in the meaning language: its definitions *are* the
    meanings ("heaven" → "Cielo, firmamento."), so each one becomes a translation."""
    entries = []
    for d in lines:
        pos_title = (d.get("pos_title") or "").lower()
        tags = ["intransitive"] if "intransitivo" in pos_title or "intransitif" in pos_title else (
            ["transitive"] if "transitivo" in pos_title or "transitif" in pos_title else [])
        translations, definitions, seen = [], [], set()
        for sense in d.get("senses", []):
            gloss = (sense.get("glosses") or [""])[-1].strip()
            if not gloss or FORM_GLOSS.match(gloss):
                continue
            definitions.append(gloss)
            example = next((e["text"] for e in sense.get("examples", []) if e.get("text")), "")
            # "(de un acento) Fuertemente regional": the label stays in the sense, not the meaning.
            for piece in _gloss_pieces(re.sub(r"^\([^)]*\)\s*", "", gloss) or gloss):
                text = piece[0].lower() + piece[1:]
                if text.lower() in seen:
                    continue
                seen.add(text.lower())
                translations.append(Translation(text=text, sense=gloss, tags=tags, gloss=gloss, example=example))
        if translations:
            entries.append(DictionaryEntry(
                part_of_speech=d.get("pos", ""), definitions=definitions[:MAX_DEFINITIONS], translations=translations,
                word=d.get("word", ""),
                forms=list(dict.fromkeys(f["form"] for f in d.get("forms", []) if f.get("form"))),
            ))
    return entries


class NativeWiktionary:
    """The Wiktionary written in the reader's language, alongside the English one. It fills
    the English edition's gaps: "heaven" has no Spanish in the English translation tables,
    the Spanish Wiktionary defines it as "cielo, firmamento"."""

    name = "Wikcionario"
    native = True

    def __init__(self, language_code: str):
        self.language_code = language_code
        self.id = f"kaikki-native1-{language_code}"

    async def lookup(self, term: str, meaning_language: str) -> list[DictionaryEntry]:
        edition, names = EDITIONS.get(meaning_language, (None, {}))
        if not edition or self.language_code not in names:
            return []
        word = term.strip()
        url = NATIVE_BASE.format(edition=edition, language=quote(names[self.language_code]),
                                 a=quote(word[:1]), ab=quote(word[:2]), word=quote(word))
        return parse_native_lines(await _fetch(url))
