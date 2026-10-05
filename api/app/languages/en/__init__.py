from functools import cached_property
from pathlib import Path

import spacy

from app.dictionary.base import Dictionary, DictionaryLink
from app.dictionary.kaikki import KaikkiDictionary, NativeWiktionary
from app.dictionary.ranking import Usage
from app.languages.base import Analysis, GrammarType
from app.languages.en.grammar import GRAMMAR_TYPES, detect_grammar
from app.languages.en.expressions import detect_expressions, load_patterns
from app.languages.en.phrasal import detect_phrasal_verbs

DATA = Path(__file__).parent / "data"

# Clitics spaCy splits off contractions ("do|n't", "it|'s"). They are not words to learn.
CLITICS = {"n't", "'s", "'re", "'ve", "'ll", "'d", "'m", "n’t", "’s", "’re", "’ve", "’ll", "’d", "’m"}

# spaCy universal POS → the part-of-speech names dictionaries use.
POS_NAMES = {"NOUN": "noun", "PROPN": "name", "VERB": "verb", "AUX": "verb", "ADJ": "adj", "ADV": "adv",
             "ADP": "prep", "PRON": "pron", "DET": "det", "CCONJ": "conj", "SCONJ": "conj", "NUM": "num", "INTJ": "intj"}

WORDREFERENCE_PAIRS = {"es", "fr", "it", "de", "pt", "nl", "sv", "ru", "pl", "ro", "cz", "gr", "tr", "zh", "ja", "ko", "ar"}


def _is_word(text: str) -> bool:
    return text.lower() not in CLITICS and any(ch.isalpha() for ch in text)


class EnglishPack:
    code = "en"
    name = "English"

    @cached_property
    def nlp(self):
        return spacy.load("en_core_web_sm", exclude=["ner"])

    @cached_property
    def prepositional_verbs(self) -> set[str]:
        lines = (DATA / "prepositional_verbs.txt").read_text(encoding="utf-8").splitlines()
        return {line.strip() for line in lines if line.strip() and not line.startswith("#")}

    @cached_property
    def expressions(self):
        return load_patterns(DATA / "expressions.txt")

    def analyze(self, text: str) -> Analysis:
        doc = self.nlp(text)
        # A paragraph break always ends a sentence: titles and headings have no final period,
        # and the parser would otherwise glue them to the next line.
        sentence_of, s_index, prev = {}, -1, None
        for tok in doc:
            breaks = prev is not None and ("\n" in prev.whitespace_ or (prev.is_space and "\n" in prev.text))
            if tok.is_sent_start or breaks or prev is None:
                if not (tok.is_space and prev is not None and "\n" in tok.text):
                    s_index += 1
            sentence_of[tok.i] = max(s_index, 0)
            prev = tok
        tokens = []
        for tok in doc:
            is_word = not tok.is_space and _is_word(tok.text)
            tokens.append(
                {
                    "t": tok.text,
                    "ws": tok.whitespace_,
                    "w": is_word,
                    # Words are keyed by surface form, like LingQ (open decision 1 in the requirements).
                    "k": tok.lower_ if is_word else None,
                    "l": tok.lemma_.lower() if is_word else None,
                    # Part of speech, to rank dictionary senses ("doubt" as a noun → "duda").
                    "p": POS_NAMES.get(tok.pos_) if is_word else None,
                    "s": sentence_of.get(tok.i, 0),
                }
            )
        units = detect_phrasal_verbs(doc, self.prepositional_verbs) + detect_expressions(doc, self.expressions)
        grammar = detect_grammar(doc, sentence_of)
        return Analysis(tokens=tokens, units=units, grammar=grammar)

    def usage(self, sentence: str, surface: str, kind: str) -> Usage:
        doc = self.nlp(sentence)
        first = surface.split()[0]
        # For a phrasal verb the dictionary entry is the whole verb, so look at the verb token.
        tok = next((t for t in doc if t.lower_ == first), None) if kind != "phrasal_verb" else next(
            (t for t in doc if t.lemma_.lower() == first and t.pos_ in ("VERB", "AUX")), None
        )
        if tok is None:
            return Usage(pos="verb" if kind == "phrasal_verb" else None)
        pos = "verb" if kind == "phrasal_verb" else POS_NAMES.get(tok.pos_)
        transitive = preposition = None
        if tok.pos_ == "VERB":
            transitive = any(c.dep_ in ("dobj", "obj", "dative") for c in tok.children)
            preposition = next((c.lower_ for c in tok.children if c.dep_ == "prep" and c.i > tok.i), None)
        return Usage(pos=pos, transitive=transitive, preposition=preposition)

    def grammar_types(self, explanation_language: str) -> dict[str, GrammarType]:
        return GRAMMAR_TYPES.get(explanation_language, GRAMMAR_TYPES["en"])

    def dictionaries(self) -> list[Dictionary]:
        # The English Wiktionary first (translation tables, forms, pronunciation), then the one
        # written in the reader's language for the meanings the first lacks.
        return [KaikkiDictionary("en", "English"), NativeWiktionary("en")]

    def dictionary_links(self, native_language: str) -> list[DictionaryLink]:
        links = [DictionaryLink("Cambridge", "https://dictionary.cambridge.org/dictionary/english/{term}")]
        if native_language in WORDREFERENCE_PAIRS:
            links.insert(0, DictionaryLink("WordReference", f"https://www.wordreference.com/en{native_language}/{{term}}"))
        links.append(
            DictionaryLink("Google Translate", f"https://translate.google.com/?sl=en&tl={native_language}&text={{term}}")
        )
        return links
