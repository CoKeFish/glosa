import pytest

from app.languages import get_language


@pytest.fixture(scope="module")
def en():
    return get_language("en")


def expressions(en, text):
    a = en.analyze(text)
    return {u["k"]: " ".join(a.tokens[i]["t"] for i in u["i"]) for u in a.units if u["kind"] == "expression"}


def test_fixed_expression(en):
    assert "by and large" in expressions(en, "By and large, the plan worked.")


def test_inflected_with_possessive_slot(en):
    found = expressions(en, "She finally made up her mind.")
    assert found.get("make up one's mind") == "made up her mind"


def test_reflexive_slot(en):
    assert "pull oneself together" in expressions(en, "He told me to pull myself together.")


def test_function_word_noise_is_skipped(en):
    found = expressions(en, "He went to the store on the corner of a busy street.")
    assert not {"to the", "on the", "of a"} & set(found)


def test_idiomatic_function_words_kept(en):
    assert "at all" in expressions(en, "I don't like it at all.")
