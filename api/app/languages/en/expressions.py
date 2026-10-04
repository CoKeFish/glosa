"""Multi-word expression detection for English (idioms, set phrases, prepositional phrases).

The list comes from Wiktionary (data/expressions.txt, built by scripts/build_expressions.py).
Entries are in dictionary form, so matching is on lemmas and placeholders are slots:

- "one's" matches a possessive: "make up one's mind" ~ "she made up her mind".
- "oneself" matches a reflexive pronoun: "pull oneself together" ~ "pull yourself together".
- "someone", "something", "somebody" and "someone's" in the middle match a short noun
  phrase: "give someone the slip" ~ "gave the guards the slip". At either end they are
  dropped: "burst someone's bubble" keeps "burst … bubble".
"""

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from spacy.tokens import Doc, Token

POSSESSIVES = {"my", "your", "his", "her", "its", "our", "their", "one's"}
POSS_SLOTS = {"one's", "someone's", "somebody's", "something's"}
REFLEXIVES = {"myself", "yourself", "himself", "herself", "itself", "ourselves", "yourselves", "themselves", "oneself"}
NP_SLOTS = {"someone", "something", "somebody", "anyone", "anything"}
MAX_SLOT_TOKENS = 4

# Function words. Expressions made only of these ("on the", "of his", "for me") fire on almost
# every sentence with their literal meaning, so they are skipped unless known idiomatic.
FUNCTION_WORDS = {
    "a", "an", "the", "of", "in", "on", "at", "to", "and", "or", "but", "it", "is", "for", "as", "by", "with",
    "that", "this", "these", "those", "be", "have", "do", "so", "all", "up", "out", "not", "no", "from", "into",
    "off", "over", "what", "i", "me", "my", "you", "your", "he", "him", "his", "she", "her", "we", "us", "our",
    "they", "them", "their", "its", "one", "more", "much", "many", "too", "very", "like", "there", "here",
    "if", "than", "then", "when", "about", "any", "some", "own",
}
IDIOMATIC_FUNCTION_ONLY = {"at all", "and all", "as of", "for all", "in all", "all out", "so as", "as is", "all that",
                           "as if", "no more", "too much"}
# Two-word "verb + particle" entries ("come to", "sleep in") are left to the phrasal verb
# detector, which tells literal from phrasal use by syntax; a plain word match cannot.
PARTICLES = {"up", "down", "in", "out", "on", "off", "to", "into", "onto", "over", "back", "away", "about", "upon",
             "through", "around", "along", "by", "for", "with", "like", "at", "from", "after", "across"}
IDIOMATIC_PAIRS = {"kind of", "sort of", "as of", "and so on", "at that"}
PRONOUNS = {"i", "me", "mine", "myself", "you", "yours", "yourself", "he", "him", "himself", "she", "hers",
            "herself", "it", "itself", "we", "us", "ours", "ourselves", "they", "them", "theirs", "themselves"}
# Two-word entries starting like this are almost always compositional in running text.
WEAK_STARTS = {"the", "a", "an", "and", "all", "other", "though", "but"}
# Common verb + word combinations Wiktionary lists as phrases that read literally in most texts.
BLOCKLIST = {"make me", "see how", "have done", "close the door", "in hell", "my name is", "for life"}


@dataclass(frozen=True)
class Pattern:
    text: str
    parts: tuple[str, ...]  # literal words, or the slot markers "<poss>", "<refl>", "<np>"


def _parse(expression: str) -> Pattern | None:
    words = expression.split()
    parts = []
    if expression in BLOCKLIST:
        return None
    if len(words) == 2 and expression not in IDIOMATIC_PAIRS and expression not in IDIOMATIC_FUNCTION_ONLY:
        if words[1] in PARTICLES or words[0] in WEAK_STARTS or PRONOUNS & set(words):
            return None
    for w in words:
        if w in POSS_SLOTS:
            parts.append("<poss>")
        elif w == "oneself":
            parts.append("<refl>")
        elif w in NP_SLOTS:
            parts.append("<np>")
        else:
            parts.append(w)
    # Slots at the edges carry no information and would swallow neighbouring words.
    while parts and parts[0] == "<np>":
        parts.pop(0)
    while parts and parts[-1] == "<np>":
        parts.pop()
    literals = [p for p in parts if not p.startswith("<")]
    if len(literals) < 2 and len(parts) < 3:
        return None
    # "piece of someone" without its slot is just "piece of": nothing idiomatic is left.
    if len(parts) < len(words) and parts[-1] in FUNCTION_WORDS | PARTICLES:
        return None
    if all(w in FUNCTION_WORDS for w in literals) and expression not in IDIOMATIC_FUNCTION_ONLY:
        return None
    return Pattern(expression, tuple(parts))


def load_patterns(path: Path) -> dict[str, list[Pattern]]:
    """Index patterns by their first literal word."""
    index: dict[str, list[Pattern]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pattern = _parse(line)
        if pattern and not pattern.parts[0].startswith("<"):
            index[pattern.parts[0]].append(pattern)
    for patterns in index.values():
        patterns.sort(key=lambda p: len(p.parts), reverse=True)  # longest first
    return index


def _word_matches(token: Token, word: str) -> bool:
    # Only verbs inflect inside an expression ("made up her mind"); nouns must match as
    # written, or "my foot" would fire on "my feet".
    return token.lower_ == word or (token.pos_ in ("VERB", "AUX") and token.lemma_.lower() == word)


def _match(doc: Doc, start: int, parts: tuple[str, ...]) -> list[int] | None:
    """Token indices of the literal words and pronoun slots if the pattern matches at `start`."""
    i, matched = start, []
    for n, part in enumerate(parts):
        if i >= len(doc):
            return None
        tok = doc[i]
        if part == "<poss>":
            if tok.lower_ not in POSSESSIVES:
                return None
            matched.append(i)
            i += 1
        elif part == "<refl>":
            if tok.lower_ not in REFLEXIVES:
                return None
            matched.append(i)
            i += 1
        elif part == "<np>":
            # A short noun phrase, ending right before the next literal word.
            following = parts[n + 1] if n + 1 < len(parts) else None
            end = None
            for length in range(1, MAX_SLOT_TOKENS + 1):
                j = i + length
                if j > len(doc) or any(not t.is_alpha and t.text not in ("'s", "’s") for t in doc[i:j]):
                    break
                if following and j < len(doc) and _word_matches(doc[j], following):
                    end = j
                    break
            if end is None:
                return None
            i = end
        else:
            if not _word_matches(tok, part):
                return None
            matched.append(i)
            i += 1
    return matched


def detect_expressions(doc: Doc, index: dict[str, list[Pattern]]) -> list[dict]:
    found = []
    taken: set[int] = set()
    for tok in doc:
        if tok.i in taken:
            continue
        candidates = index.get(tok.lower_, []) + (index.get(tok.lemma_.lower(), []) if tok.lemma_.lower() != tok.lower_ else [])
        best: tuple[Pattern, list[int]] | None = None
        for pattern in candidates:
            indices = _match(doc, tok.i, pattern.parts)
            if indices and (best is None or indices[-1] - indices[0] > best[1][-1] - best[1][0]):
                best = (pattern, indices)
        if best is None:
            continue
        pattern, indices = best
        # Expressions do not cross sentence boundaries.
        if doc[indices[0]].sent.start != doc[indices[-1]].sent.start:
            continue
        taken.update(range(indices[0], indices[-1] + 1))
        contiguous = indices == list(range(indices[0], indices[-1] + 1))
        found.append({"k": pattern.text, "kind": "expression", "i": indices, "sep": not contiguous})
    return found
