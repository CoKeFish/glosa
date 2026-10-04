from app.routers.books import _phrase_units


def tok(t, lemma=None, w=True):
    return {"t": t, "ws": " ", "w": w, "k": t.lower() if w else None, "l": (lemma or t).lower() if w else None, "s": 0}


def test_saved_expression_matches_inflected_form():
    tokens = [tok("She"), tok("finally"), tok("made", "make"), tok("up"), tok("her"), tok("mind"), tok(".", w=False)]
    units = _phrase_units(tokens, [("make up one's mind", "expression")])
    assert units == [{"k": "make up one's mind", "kind": "expression", "i": [2, 3, 4, 5], "sep": False}]


def test_saved_phrase_needs_every_word():
    tokens = [tok("by"), tok("and"), tok("small")]
    assert _phrase_units(tokens, [("by and large", "expression")]) == []
