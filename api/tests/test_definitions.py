from app.dictionary.ranking import Usage
from app.translation import _unchanged


def test_echoed_translation_is_detected():
    assert _unchanged("In relating", "In relating")
    assert _unchanged("In relating", "in relating.")
    assert not _unchanged("In relating", "En relación con")
from app.dictionary.service import _definition_pieces

RESULTS = [{
    "term": "spring up",
    "entries": [
        {"part_of_speech": "verb", "definitions": ["To appear suddenly.", "Used other than figuratively: see spring, up."],
         "forms": [], "word": "spring up"},
    ],
}, {
    "term": "by degrees",
    "entries": [{"part_of_speech": "adv", "definitions": ["In gradual steps; bit by bit."], "forms": []}],
}]


def test_definitions_split_and_skip_pointers():
    pieces = [p for p, _, _ in _definition_pieces(RESULTS, Usage(pos="verb"))]
    assert pieces[0] == "To appear suddenly"
    assert "In gradual steps" in pieces and "bit by bit" in pieces
    assert not any(p.startswith("Used other than") for p in pieces)
