import pytest

from app.languages import get_language


@pytest.fixture(scope="module")
def en():
    return get_language("en")


def phrasal(en, text):
    a = en.analyze(text)
    return {(u["k"], u["sep"]) for u in a.units if u["kind"] == "phrasal_verb"}


def grammar(en, text):
    return {g["type"] for g in en.analyze(text).grammar}


# --- phrasal verbs -------------------------------------------------------

def test_particle_phrasal_verb(en):
    assert ("give up", False) in phrasal(en, "She never gives up.")


def test_separated_phrasal_verb_uses_base_form(en):
    assert ("turn off", True) in phrasal(en, "He turned the lights off before leaving.")


def test_phrasal_vs_literal(en):
    assert any(k == "look up" for k, _ in phrasal(en, "She looked up the word in the dictionary."))
    assert ("run up", False) in phrasal(en, "He ran up a huge bill.")
    assert not any(k.startswith("run") for k, _ in phrasal(en, "They ran up the hill."))
    assert not any(k.startswith("climb") for k, _ in phrasal(en, "He climbed up the ladder."))


@pytest.mark.xfail(reason="Same syntax as 'looked up the address'; only meaning tells them apart. "
                          "The AI explanation confirms or rejects the unit (is_phrasal_verb).", strict=True)
def test_literal_with_phrasal_syntax(en):
    assert not any(k.startswith("look") for k, _ in phrasal(en, "She looked up the chimney."))


def test_prepositional_verb_from_list(en):
    assert any(k == "look after" for k, _ in phrasal(en, "My grandmother looks after the children."))


def test_three_part_verb(en):
    assert any(k == "put up with" for k, _ in phrasal(en, "I can't put up with this noise anymore."))


def test_plain_verb_has_no_unit(en):
    assert phrasal(en, "They walked to the station.") == set()


# --- tokens --------------------------------------------------------------

def test_tokens_rebuild_text(en):
    text = "Don't stop.\n\nIt's late, isn't it?"
    a = en.analyze(text)
    assert "".join(t["t"] + t["ws"] for t in a.tokens) == text


def test_paragraph_break_ends_sentence(en):
    a = en.analyze("The Tomb\n\n(1917)\n\nIn relating the circumstances, I am aware.")
    words = {t["t"]: t["s"] for t in a.tokens if t["w"]}
    assert words["Tomb"] != words["relating"]
    assert words["relating"] == words["aware"]


def test_contraction_clitics_are_not_words(en):
    a = en.analyze("I don't know.")
    assert [t["k"] for t in a.tokens if t["w"]] == ["i", "do", "know"]


# --- grammar -------------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected",
    [
        ("I have lived here for ten years.", "present_perfect"),
        ("She has been working all day.", "present_perfect_continuous"),
        ("They had left before we arrived.", "past_perfect"),
        ("We are reading a book.", "present_continuous"),
        ("He was sleeping when I called.", "past_continuous"),
        ("It will rain tomorrow.", "future_will"),
        ("I am going to call her.", "going_to"),
        ("The house was built in 1990.", "passive"),
        ("If it rains, we will stay home.", "conditional_clause"),
        ("The man who lives next door is a doctor.", "relative_clause"),
        ("This book is better than that one.", "comparative"),
        ("It is the tallest building in the city.", "superlative"),
        ("There are three apples on the table.", "there_be"),
        ("You should study more.", "modal"),
        ("I would have helped you.", "conditional_perfect"),
        ("We used to live in Madrid.", "used_to"),
    ],
)
def test_grammar(en, text, expected):
    assert expected in grammar(en, text)
