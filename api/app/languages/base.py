"""Contract every language pack implements.

A language pack owns everything that depends on the language being read:
splitting text into words, finding multi-word units such as phrasal verbs,
labelling grammar structures, and which dictionaries can look words up.
Adding a language means writing one pack and registering it; nothing else
in the app knows about specific languages.
"""

from dataclasses import dataclass, field
from typing import Protocol

from app.dictionary.base import Dictionary, DictionaryLink
from app.dictionary.ranking import Usage


@dataclass
class Analysis:
    # Each token: {"t": text, "ws": trailing whitespace, "w": is a word,
    #              "k": lookup key, "l": lemma, "s": sentence index}
    tokens: list[dict] = field(default_factory=list)
    # Multi-word units: {"k": key, "kind": "phrasal_verb", "sub": subtype,
    #                    "i": [token indices], "sep": separated}
    units: list[dict] = field(default_factory=list)
    # Grammar structures: {"type": id, "s": sentence index, "i": [token indices]}
    grammar: list[dict] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        return sum(1 for t in self.tokens if t["w"])


@dataclass(frozen=True)
class GrammarType:
    id: str
    label: str
    explanation: str


class LanguagePack(Protocol):
    code: str
    name: str

    def analyze(self, text: str) -> Analysis: ...

    def usage(self, sentence: str, surface: str, kind: str) -> "Usage":
        """How `surface` is used in `sentence` (part of speech, transitivity), to rank dictionary senses."""
        ...

    def grammar_types(self, explanation_language: str) -> dict[str, GrammarType]:
        """Labels and explanations, in the reader's explanation language (falls back to English)."""
        ...

    def dictionaries(self) -> list[Dictionary]: ...

    def dictionary_links(self, meaning_language: str) -> list[DictionaryLink]: ...
