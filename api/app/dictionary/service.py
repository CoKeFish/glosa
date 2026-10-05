import re

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.dictionary import ranking
from app.dictionary.base import Dictionary, DictionaryError
from app.languages import get_language
from app.models import DictionaryCache
from app import translation_cache
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


async def _translate_sentence(session: Session, sentence: str, source: str, target: str) -> str:
    """Local machine translation of the sentence, used as a ranking signal. Empty if unavailable."""
    if not sentence:
        return ""
    try:
        return await translation_cache.cached(session, "local", source, target, sentence,
                                              lambda: LocalTranslator().translate(sentence, source, target))
    except TranslationError:
        return ""


# Wiktionary (English edition) writes its definitions in English, whatever the word's language.
DEFINITIONS_LANGUAGE = "en"
MAX_DEFINITION_PIECES = 6
# Definitions that only point elsewhere; translating them gives nothing useful.
NON_GLOSSES = re.compile(r"^(used other than|alternative|misspelling|obsolete form|archaic form|(simple )?past|"
                         r"present participle|plural of|third-person|eye dialect|abbreviation of)", re.I)
DEGREE_FORM = re.compile(r"^(comparative|superlative) (?:degree |form )?of \w[\w-]*: (?P<meaning>(?:more|most) .+)$", re.I)


def _definition_pieces(results: list[dict], usage: ranking.Usage,
                       only_pos: bool = False) -> list[tuple[str, dict, str]]:
    """Short English glosses worth translating: (piece, entry, full definition), best entries first."""
    # English definitions only: the other Wiktionary's are already in the reader's language.
    entries = [(r["term"], e) for r in results if not r.get("native") for e in r["entries"]]
    if only_pos:
        entries = [(t, e) for t, e in entries if e["part_of_speech"] == usage.pos]
    if usage.pos:
        entries.sort(key=lambda te: te[1]["part_of_speech"] != usage.pos)
    pieces = []
    for term, entry in entries:
        for definition in entry["definitions"]:
            if NON_GLOSSES.match(definition):
                continue
            # "comparative form of broad: more broad" → translate "more broad" ("más amplio"),
            # the meaning of this very form, not the grammar label.
            degree = DEGREE_FORM.match(definition)
            if degree:
                pieces.append((degree["meaning"].rstrip("."), {**entry, "term": term, "degree": True}, definition))
                continue
            # "In any case; anyway." → two short glosses, each translates cleanly.
            for piece in re.split(r";\s*", definition.rstrip(".")):
                piece = re.sub(r"\s*\(.*?\)\s*", " ", piece).strip()
                if 0 < len(piece.split()) <= 8:
                    pieces.append((piece, {**entry, "term": term}, definition))
                if len(pieces) >= MAX_DEFINITION_PIECES:
                    return pieces
    return pieces


async def _translated_definitions(session: Session, results: list[dict], usage: ranking.Usage,
                                  meaning_language: str, only_pos: bool = False) -> list[dict]:
    """When the dictionary has no translations into the reader's language, translate its
    English definitions locally: "To appear suddenly" → "Aparecer de repente". Bare words
    and idioms translate badly on their own ("spring up" → "primavera"); plain definitions do not."""
    pieces = _definition_pieces(results, usage, only_pos)
    if not pieces:
        return []
    try:
        texts = await translation_cache.cached_many(
            session, "local", DEFINITIONS_LANGUAGE, meaning_language, [p for p, _, _ in pieces],
            lambda missing: LocalTranslator().translate_many(missing, DEFINITIONS_LANGUAGE, meaning_language))
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
            **({"degree_form": True} if entry.get("degree") else {}),
        })
    return candidates


def _pronunciation(results: list[dict], usage: ranking.Usage, surface: str, best: dict | None) -> dict | None:
    """IPA and recordings for the word as written, from the sense that fits the sentence.

    Only entries of the surface form itself count: "led" must not play "lead". Pronunciation
    follows etymology ("lead" the metal /lɛd/, "lead" to guide /liːd/), and Wiktionary lists it
    once per etymology, so the etymology of the best-fitting translation decides; failing
    that, the part of speech used in the sentence.
    """
    # The Wiktionary in the reader's language carries no pronunciation (see kaikki.NativeWiktionary).
    entries = [e for r in results if r["term"] == surface and not r.get("native") for e in r["entries"]]
    if not entries:
        return None
    if best and best.get("term") == surface and not best.get("native"):
        etymology = best.get("etymology")
    else:
        by_pos = sorted(entries, key=lambda e: e["part_of_speech"] != usage.pos)
        etymology = by_pos[0].get("etymology")
    candidates = sorted(entries, key=lambda e: (e.get("etymology") != etymology, not e.get("audio"), not e.get("ipa")))
    chosen = candidates[0]
    if not chosen.get("ipa") and not chosen.get("audio"):
        return None
    return {"ipa": chosen.get("ipa", []), "audio": chosen.get("audio", [])}


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
            native = getattr(dictionary, "native", False)
            try:
                entries = await _entries(session, dictionary, term, meaning_language)
            except DictionaryError as exc:
                errors.append(str(exc))
                continue
            if not entries:
                continue
            results.append({"term": term, "source": dictionary.name, "entries": entries, "native": native})
            for entry in entries:
                for t in entry["translations"]:
                    candidates.append({**t, "term": term, "word": entry.get("word") or term,
                                       "part_of_speech": entry["part_of_speech"], "forms": entry.get("forms", []),
                                       "etymology": entry.get("etymology", 0), "native": native})
                if len(seen) < 4:
                    pending.extend(f.lower() for f in entry["form_of"])
                    # A word with no translations of its own that refers to another one
                    # ("upon" → "on") borrows that word's translations.
                    if not entry["translations"]:
                        pending.extend(w.lower() for w in entry.get("see", []))
        # Proper nouns are entered capitalised ("Ohio", "Harvard"): nothing in lower case → try that.
        if not pending and not results and term == terms[0].strip().lower() and term[:1].isalpha():
            pending.append(term.capitalize())

    # Both Wiktionaries often agree ("mentir"): keep one, or the tie hides which meaning fits.
    unique_candidates, keys = [], set()
    for c in candidates:
        key = (c["text"].lower(), c["part_of_speech"])
        if key not in keys:
            keys.add(key)
            unique_candidates.append(c)
    candidates = unique_candidates

    # The sentence translation is shown in the panel and ranks candidates, so always fetch it.
    context_translation = await _translate_sentence(session, context, language, meaning_language)
    if meaning_language != DEFINITIONS_LANGUAGE:
        if not candidates:
            candidates = await _translated_definitions(session, results, usage, meaning_language)
        elif usage.pos and not any(c["part_of_speech"] == usage.pos for c in candidates):
            # The word is used as, say, an adjective, but only another part of speech has
            # translations ("broader": only the slang noun "broad" is translated). Translate
            # the definitions of the part of speech actually used.
            candidates += await _translated_definitions(session, results, usage, meaning_language, only_pos=True)
        # "broader" is "comparative form of broad: more broad": its own meaning ("más amplio")
        # beats the base word's, even when the base word has translations.
        own = [r for r in results if r["term"] == surface and not r.get("native")]
        if any(DEGREE_FORM.match(d) for r in own for e in r["entries"] for d in e["definitions"]):
            candidates += [c for c in await _translated_definitions(session, own, usage, meaning_language)
                           if c.get("degree_form")]
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
        "pronunciation": _pronunciation(results, usage, surface, ranked[0] if ranked else None),
        "translations": unique,
        "sentence_translation": context_translation,
        "usage": {"pos": usage.pos, "transitive": usage.transitive},
        "results": results,
        "links": links,
        "errors": errors,
    }
