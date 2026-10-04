import re

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.dictionary import ranking
from app.dictionary.base import Dictionary, DictionaryError
from app.languages import get_language
from app.models import DictionaryCache
from app.translation import LocalTranslator, TranslationError


async def _entries(session: Session, dictionary: Dictionary, term: str, meaning_language: str) -> list[dict]:
    cache_key = f"{dictionary.id}:{meaning_language}:{term}"
    cached = session.get(DictionaryCache, cache_key)
    if cached is not None:
        return cached.entries
    entries = [e.to_dict() for e in await dictionary.lookup(term, meaning_language)]
    session.merge(DictionaryCache(key=cache_key, entries=entries))
    session.commit()
    return entries


_sentence_cache: dict[tuple[str, str, str], str] = {}


async def _translate_sentence(sentence: str, source: str, target: str) -> str:
    """Local machine translation of the sentence, used as a ranking signal. Empty if unavailable."""
    if not sentence:
        return ""
    key = (sentence, source, target)
    if key not in _sentence_cache:
        try:
            _sentence_cache[key] = await LocalTranslator().translate(sentence, source, target)
        except TranslationError:
            return ""
        if len(_sentence_cache) > 2000:
            _sentence_cache.pop(next(iter(_sentence_cache)))
    return _sentence_cache[key]


# Wiktionary (English edition) writes its definitions in English, whatever the word's language.
DEFINITIONS_LANGUAGE = "en"
MAX_DEFINITION_PIECES = 6
# Definitions that only point elsewhere; translating them gives nothing useful.
NON_GLOSSES = re.compile(r"^(used other than|alternative|misspelling|obsolete form|archaic form|(simple )?past|"
                         r"present participle|plural of|third-person|eye dialect|abbreviation of)", re.I)


def _definition_pieces(results: list[dict], usage: ranking.Usage) -> list[tuple[str, dict, str]]:
    """Short English glosses worth translating: (piece, entry, full definition), best entries first."""
    entries = [(r["term"], e) for r in results for e in r["entries"]]
    if usage.pos:
        entries.sort(key=lambda te: te[1]["part_of_speech"] != usage.pos)
    pieces = []
    for term, entry in entries:
        for definition in entry["definitions"]:
            if NON_GLOSSES.match(definition):
                continue
            # "In any case; anyway." → two short glosses, each translates cleanly.
            for piece in re.split(r";\s*", definition.rstrip(".")):
                piece = re.sub(r"\s*\(.*?\)\s*", " ", piece).strip()
                if 0 < len(piece.split()) <= 8:
                    pieces.append((piece, {**entry, "term": term}, definition))
                if len(pieces) >= MAX_DEFINITION_PIECES:
                    return pieces
    return pieces


async def _translated_definitions(results: list[dict], usage: ranking.Usage, meaning_language: str) -> list[dict]:
    """When the dictionary has no translations into the reader's language, translate its
    English definitions locally: "To appear suddenly" → "Aparecer de repente". Bare words
    and idioms translate badly on their own ("spring up" → "primavera"); plain definitions do not."""
    pieces = _definition_pieces(results, usage)
    if not pieces:
        return []
    try:
        texts = await LocalTranslator().translate_many([p for p, _, _ in pieces], DEFINITIONS_LANGUAGE, meaning_language)
    except TranslationError:
        return []
    candidates = []
    for text, (piece, entry, definition) in zip(texts, pieces):
        text = text.strip().rstrip(".")
        # "To appear suddenly" comes back as "para aparecer…"; the infinitive is what we want.
        if piece.lower().startswith("to ") and meaning_language == "es":
            text = re.sub(r"^para\s+", "", text, flags=re.I)
        if not text or text.lower() == piece.lower():  # left untranslated
            continue
        candidates.append({
            "text": text[0].lower() + text[1:], "sense": definition, "term": entry["term"],
            "word": entry.get("word") or entry["term"], "part_of_speech": entry["part_of_speech"],
            "forms": entry.get("forms", []), "tags": [], "from_definition": True,
        })
    return candidates


async def lookup(
    session: Session,
    language: str,
    terms: list[str],
    meaning_language: str,
    *,
    context: str = "",
    surface: str | None = None,
    kind: str = "word",
) -> dict:
    """Look the terms up in every dictionary of the language pack and rank the translations.

    `terms` usually holds the surface form and the lemma ("looked", "look"). Inflected forms
    the dictionary points to ("led" → "lead") are followed one step. Translations are then
    ordered by how well they fit the sentence (see `ranking`).
    """
    pack = get_language(language)
    surface = (surface or terms[0]).strip().lower()
    usage = pack.usage(context, surface, kind) if context else ranking.Usage()

    pending = [t.strip().lower() for t in terms if t and t.strip()]
    seen: set[str] = set()
    results, candidates, errors = [], [], []
    while pending:
        term = pending.pop(0)
        if term in seen:
            continue
        seen.add(term)
        for dictionary in pack.dictionaries():
            try:
                entries = await _entries(session, dictionary, term, meaning_language)
            except DictionaryError as exc:
                errors.append(str(exc))
                continue
            if not entries:
                continue
            results.append({"term": term, "source": dictionary.name, "entries": entries})
            for entry in entries:
                for t in entry["translations"]:
                    candidates.append({**t, "term": term, "word": entry.get("word") or term,
                                       "part_of_speech": entry["part_of_speech"], "forms": entry.get("forms", [])})
                if len(seen) < 4:
                    pending.extend(f.lower() for f in entry["form_of"])

    # The sentence translation is shown in the panel and ranks candidates, so always fetch it.
    context_translation = await _translate_sentence(context, language, meaning_language)
    if not candidates and meaning_language != DEFINITIONS_LANGUAGE:
        candidates = await _translated_definitions(results, usage, meaning_language)
    ranked = await run_in_threadpool(
        ranking.rank, candidates, surface=surface, usage=usage, context=context,
        meaning_language=meaning_language, context_translation=context_translation,
    )
    unique, used = [], set()
    for t in ranked:
        if t["text"].lower() not in used:
            used.add(t["text"].lower())
            unique.append({k: t[k] for k in ("text", "sense", "term", "part_of_speech", "score")}
                          | {"fits": t.get("fits", False), "from_definition": t.get("from_definition", False)})

    links = [{"name": link.name, "url": link.url(terms[0])} for link in pack.dictionary_links(meaning_language)] if terms else []
    return {
        "translations": unique,
        "sentence_translation": context_translation,
        "usage": {"pos": usage.pos, "transitive": usage.transitive},
        "results": results,
        "links": links,
        "errors": errors,
    }
