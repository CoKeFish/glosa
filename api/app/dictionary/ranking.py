"""Order dictionary translations by how well they fit the sentence. No AI service involved.

Signals, strongest first:

0. Sentence translation: the local machine translator renders the whole sentence; a
   candidate that appears in it ("…que han llevado a mi confinamiento" → "llevar") is
   the meaning that fits this context.
1. Form: an inflected word only belongs to entries that list it. "led" is a form of
   lead (to guide), not of lead (to cover with lead, past "leaded").
2. Part of speech: "doubt" used as a noun prefers "duda" over "dudar".
3. Valency: a verb with a direct object prefers transitive senses, one without prefers
   intransitive ones ("which have led to my confinement" is intransitive).
4. Pattern: a verb followed by a preposition ("led to") prefers senses whose gloss or
   example uses the same pattern ("Eating junk food leads to…").
5. Context: a small local embedding model compares the sentence with the description
   of each sense and favours the closest.
6. Frequency: between near ties, common words in the meaning language win
   ("duda" over "dubio").
"""

import re
from dataclasses import dataclass
from functools import cache

import numpy as np

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


@dataclass
class Usage:
    """How the selected word is used in its sentence, from the language pack's parser."""

    pos: str | None = None
    transitive: bool | None = None
    preposition: str | None = None  # first preposition attached to a verb ("to" in "led to")


def _frequency(text: str, language: str) -> float:
    """Zipf frequency (0–8) of a word or phrase in the meaning language; 0 when unknown."""
    try:
        from wordfreq import zipf_frequency

        return zipf_frequency(text, language)
    except (ImportError, LookupError, ValueError):
        return 0.0


@cache
def _embedder():
    import os

    from fastembed import TextEmbedding

    return TextEmbedding(model_name=EMBEDDING_MODEL, cache_dir=os.environ.get("FASTEMBED_CACHE_PATH"))


def _similarities(context: str, texts: list[str]) -> list[float]:
    if not context or not texts:
        return [0.0] * len(texts)
    vectors = list(_embedder().embed([context, *texts]))
    ctx = vectors[0] / np.linalg.norm(vectors[0])
    return [float(np.dot(ctx, v / np.linalg.norm(v))) for v in vectors[1:]]


def _transitivity(candidate: dict) -> bool | None:
    tags = candidate.get("tags") or []
    sense = (candidate.get("sense") or "").lower()
    if "intransitive" in tags or sense.startswith("intransitive"):
        return False
    if "transitive" in tags or sense.startswith("transitive"):
        return True
    return None


def _uses_pattern(candidate: dict, preposition: str) -> bool:
    words = {w.lower() for w in [candidate.get("word", ""), *(candidate.get("forms") or [])] if w}
    text = " ".join(filter(None, [candidate.get("sense"), candidate.get("gloss"), candidate.get("example")])).lower()
    return any(re.search(rf"\b{re.escape(w)} {re.escape(preposition)}\b", text) for w in words)


def _stem(word: str) -> str:
    """Stem of a dictionary form: the infinitive ending or final vowel removed
    ("llevar" → "llev", "duda" → "dud", "estar" → "est")."""
    word = word.lower().removesuffix("se")
    for ending in ("ar", "er", "ir"):
        if word.endswith(ending) and len(word) > 3:
            return word[: -len(ending)]
    return word[:-1] if len(word) > 3 and word[-1] in "aeo" else word


# What may follow a Spanish stem in an inflected form: verb endings, participles, gerunds,
# plurals, and attached clitics. "están" is "est" + "án"; "mental" is not "ment" + anything here.
_ES_INFLECTION = re.compile(
    r"(?:oy|ás|á|án|amos|áis|uve|uvo|uvieron|"
    r"a|as|an|o|os|e|es|en|emos|imos|éis|ís|ó|é|í|aste|iste|aron|ieron|ió|"
    r"aba|abas|aban|ábamos|ía|ías|ían|íamos|ado|ada|ados|adas|ido|ida|idos|idas|ando|iendo|yendo|"
    r"ar|er|ir|aré|ará|arán|eré|erá|erán|iré|irá|irán|aría|arían|ería|erían|iría|irían|"
    r"ase|ara|aran|iera|ieran|iese|s|n)?"
    r"(?:se|lo|la|le|los|las|les|me|te|nos)?"
)


def _is_form_of(word: str, dictionary_word: str, language: str) -> bool:
    """`word` (from the translation) is an inflected form of `dictionary_word`."""
    word, base = word.lower(), dictionary_word.lower()
    if word == base:
        return True
    stem = _stem(base)
    if len(stem) < 3 or not word.startswith(stem):
        return False
    rest = word[len(stem):]
    if language == "es":
        return _ES_INFLECTION.fullmatch(rest) is not None
    return len(rest) <= 3  # other languages: a short ending only


def _content_words(text: str) -> list[str]:
    return [p for p in re.findall(r"\w+", text.lower()) if len(p) > 2]


def _appears_in(candidate_text: str, translation: str, language: str = "es") -> bool:
    words = re.findall(r"\w+", translation.lower())
    # Every content word of a multi-word candidate must be there: "mirar hacia arriba"
    # should not match a sentence that only says "miró".
    parts = _content_words(candidate_text)
    if not parts or not words:
        return False
    return all(any(_is_form_of(w, p, language) for w in words) for p in parts)


def _head_appears_in(candidate_text: str, translation: str, language: str = "es") -> bool:
    """The first content word of a multi-word candidate appears in the translation."""
    parts = _content_words(candidate_text)
    if len(parts) < 2:
        return False
    return any(_is_form_of(w, parts[0], language) for w in re.findall(r"\w+", translation.lower()))


def rank(candidates: list[dict], *, surface: str, usage: Usage, context: str, meaning_language: str = "es",
         context_translation: str = "") -> list[dict]:
    """Return candidates best-first, each with a "score" and a "fits" flag on the winner.

    A candidate is a translation dict carrying its entry's data: text, sense, tags,
    part_of_speech, forms (inflections the entry lists) and word (the headword).
    """
    if not candidates:
        return []
    surface = surface.lower()
    sense_texts = [
        " ".join(filter(None, [c.get("sense"), c.get("gloss"), c.get("example")])) or c["text"] for c in candidates
    ]
    try:
        similarity = _similarities(context, sense_texts)
    except Exception:  # the model is an optional refinement; ranking still works without it
        similarity = [0.0] * len(candidates)

    scored = []
    for order, (c, sim) in enumerate(zip(candidates, similarity)):
        score = 0.0
        forms = [f.lower() for f in c.get("forms") or []]
        if surface != c.get("word", "").lower() and forms and surface not in forms:
            score -= 3.0  # this entry does not inflect that way
        if usage.pos and c.get("part_of_speech") == usage.pos:
            score += 2.0
        if c.get("degree_form") and c.get("term", "").lower() == surface:
            score += 2.0  # "broader" → "más amplio": the meaning of this exact comparative form
        if context_translation:
            if _appears_in(c["text"], context_translation, meaning_language):
                score += 3.0
            elif _head_appears_in(c["text"], context_translation, meaning_language):
                # "estar ubicado" when the translation says "están fuera": the verb is there,
                # its complement is not. Weaker evidence, but it beats a candidate with none.
                score += 1.5
        trans = _transitivity(c)
        if usage.transitive is not None and trans is not None:
            score += 0.5 if trans == usage.transitive else -0.5
        if usage.preposition and _uses_pattern(c, usage.preposition):
            score += 1.5
        score += 2.0 * sim
        score += 0.15 * _frequency(c["text"], meaning_language)
        score -= 0.01 * order  # keep dictionary order as the tie-breaker
        scored.append((score, c))

    scored.sort(key=lambda s: s[0], reverse=True)
    result = [{**c, "score": round(score, 3)} for score, c in scored]
    # Only claim a best fit when it clearly beats the runner-up.
    if len(result) == 1 or result[0]["score"] - result[1]["score"] > 0.15:
        result[0]["fits"] = True
    return result
