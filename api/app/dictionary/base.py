from dataclasses import asdict, dataclass, field
from typing import Protocol


@dataclass
class Translation:
    text: str  # in the reader's meaning language, e.g. "apagar"
    sense: str = ""  # which meaning it translates, in the dictionary's language
    # Details of that sense, used to rank translations against the sentence.
    tags: list[str] = field(default_factory=list)  # e.g. "transitive"
    gloss: str = ""
    example: str = ""


@dataclass
class DictionaryEntry:
    part_of_speech: str
    definitions: list[str]
    examples: list[str] = field(default_factory=list)
    translations: list[Translation] = field(default_factory=list)
    # When the term is an inflected form ("led"), the base forms it comes from ("lead").
    form_of: list[str] = field(default_factory=list)
    word: str = ""
    # Inflections of this entry ("led" for lead/guide, "leaded" for lead/metal).
    forms: list[str] = field(default_factory=list)
    # Pronunciation of this entry: it differs between entries ("lead" the metal vs to lead).
    ipa: list[str] = field(default_factory=list)
    audio: list[dict] = field(default_factory=list)  # {"url": ..., "accent": "US" | "UK" | ...}
    # Entries of the same word and etymology share a pronunciation, which Wiktionary lists once.
    etymology: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DictionaryLink:
    """An external dictionary opened in the browser, like LingQ's integrated dictionaries."""

    name: str
    url_template: str  # "{term}" is replaced by the URL-encoded term

    def url(self, term: str) -> str:
        from urllib.parse import quote

        return self.url_template.replace("{term}", quote(term))


class DictionaryError(Exception):
    pass


class Dictionary(Protocol):
    id: str
    name: str

    async def lookup(self, term: str, meaning_language: str) -> list[DictionaryEntry]:
        """Entries for the term, with translations into meaning_language when the source has them."""
        ...
