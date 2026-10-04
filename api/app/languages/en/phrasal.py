"""Phrasal verb detection for English.

Two sources, because neither is enough alone:

- The dependency parser marks verb particles ("turn the light off", "give up") with the
  `prt` relation. It decides per occurrence, so "look up the word" (particle) and "look up
  the chimney" (preposition) come out different, which a word list cannot do.
- Prepositional verbs ("look after the kids", "come across a word") are parsed as an
  ordinary verb + preposition. Those are only accepted when the combination is in the
  curated list, which keeps literal uses out.
"""

from spacy.tokens import Doc, Token

FOLLOWER_DEPS = {"prt", "prep", "advmod", "agent"}


def _followers(verb: Token) -> list[Token]:
    """Particles and prepositions attached to the verb, after it, in text order."""
    found = [c for c in verb.children if c.i > verb.i and c.dep_ in FOLLOWER_DEPS]
    # "look forward to": "to" may hang from "forward" instead of the verb.
    for c in list(found):
        found.extend(g for g in c.children if g.dep_ == "prep" and g.i > c.i)
    return sorted(set(found), key=lambda t: t.i)


def _unit(key: str, sub: str, tokens: list[Token]) -> dict:
    indices = sorted(t.i for t in tokens)
    contiguous = indices == list(range(indices[0], indices[-1] + 1))
    return {"k": key, "kind": "phrasal_verb", "sub": sub, "i": indices, "sep": not contiguous}


def detect_phrasal_verbs(doc: Doc, prepositional_verbs: set[str]) -> list[dict]:
    units = []
    for verb in doc:
        if verb.pos_ not in ("VERB", "AUX"):
            continue
        lemma = verb.lemma_.lower()
        followers = _followers(verb)
        if not followers:
            continue

        particle = next((f for f in followers if f.dep_ == "prt"), None)
        if particle is not None:
            parts = [verb, particle]
            key = f"{lemma} {particle.lower_}"
            # Three-part verbs: "put up with", "run out of".
            after = [f for f in followers if f.i > particle.i and f.dep_ != "prt"]
            if after and f"{key} {after[0].lower_}" in prepositional_verbs:
                parts.append(after[0])
                key = f"{key} {after[0].lower_}"
            units.append(_unit(key, "particle", parts))
            continue

        # No particle: accept the longest listed combination of the next one or two words.
        first = followers[0]
        candidates = []
        if len(followers) > 1:
            candidates.append([first, followers[1]])
        candidates.append([first])
        for extra in candidates:
            key = " ".join([lemma, *(t.lower_ for t in extra)])
            if key in prepositional_verbs:
                units.append(_unit(key, "prepositional", [verb, *extra]))
                break
    return units
