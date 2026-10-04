from app.dictionary.kaikki import parse_lines

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
