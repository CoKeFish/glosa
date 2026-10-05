from app.dictionary.kaikki import parse_lines, parse_native_lines

TURN_OFF = {
    "pos": "verb",
    "senses": [{"glosses": ["To power down, to switch off."]}, {"glosses": ["To disgust."]}],
    "translations": [
        {"lang_code": "es", "word": "apagar", "sense": "to power down"},
        {"lang_code": "fr", "word": "éteindre", "sense": "to power down"},
        {"lang_code": "es", "word": "repugnar", "sense": "to disgust"},
        {"lang_code": "es", "word": "apagar", "sense": "duplicate"},
    ],
}
LED = {"pos": "verb", "senses": [{"glosses": ["simple past of lead"], "form_of": [{"word": "lead"}]}]}


def test_translations_in_meaning_language_only():
    [entry] = parse_lines([TURN_OFF], "es")
    assert [t.text for t in entry.translations] == ["apagar", "repugnar"]
    assert entry.translations[0].sense == "to power down"
    assert entry.definitions[0].startswith("To power down")


def test_inflected_form_points_to_base():
    [entry] = parse_lines([LED], "es")
    assert entry.form_of == ["lead"]
    assert entry.translations == []


def test_native_wiktionary_definitions_become_meanings():
    lie = {"word": "lie", "pos": "verb", "pos_title": "Verbo intransitivo", "senses": [
        {"glosses": ["Yacer, estar acostado, estar tumbado."]},
        {"glosses": ["Residir, encontrarse, ubicarse, estar colocado o ubicado."],
         "examples": [{"text": "The origins of this disaster lie farther north."}]}],
        "forms": [{"form": "lain"}, {"form": "lay"}]}
    led = {"word": "led", "pos": "verb", "senses": [{"glosses": ["Pasado simple del verbo (to) lead."]}]}
    gonna = {"word": "gonna", "pos": "contraction", "senses": [{"glosses": ['Contracción de going y to, "ir a".']}]}
    broad = {"word": "broad", "pos": "adj", "senses": [{"glosses": ["(de un acento) Fuertemente regional."]}]}
    [entry] = parse_native_lines([lie])
    assert [t.text for t in entry.translations][:4] == ["yacer", "estar acostado", "estar tumbado", "residir"]
    assert entry.translations[0].tags == ["intransitive"] and entry.forms == ["lain", "lay"]
    assert entry.translations[3].example.startswith("The origins")
    assert parse_native_lines([led]) == []  # only names a form: the English edition follows it
    assert [t.text for t in parse_native_lines([gonna])[0].translations] == ['contracción de going y to, "ir a"']
    assert parse_native_lines([broad])[0].translations[0].text == "fuertemente regional"


def test_reference_entry_points_to_the_word_it_refers_to():
    upon = {"word": "upon", "pos": "prep", "senses": [
        {"glosses": ["alternative to on in most, though not all, prepositional uses."], "links": [["on", "on#English"]]}]}
    whilst = {"word": "whilst", "pos": "conj", "senses": [{"glosses": ["Alternative form of while"],
                                                           "alt_of": [{"word": "while"}]}]}
    bank = {"word": "bank", "pos": "noun", "senses": [{"glosses": ["The edge of a river."], "links": [["river", "river"]]}]}
    assert parse_lines([upon], "es")[0].see == ["on"]
    assert parse_lines([whilst], "es")[0].see == ["while"]
    assert parse_lines([bank], "es")[0].see == []  # an ordinary definition is not a reference
