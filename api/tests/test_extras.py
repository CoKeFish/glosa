from app.dictionary.kaikki import parse_lines
from app.extras import CATALOG, PRESETS
from app.offline_dictionary import reduce_line


def test_presets_only_name_listed_extras():
    for name, ids in PRESETS.items():
        for extra_id in ids:
            assert extra_id in CATALOG and not CATALOG[extra_id].hidden, (name, extra_id)


def test_every_container_extra_has_an_alias_the_code_uses():
    aliases = {e.container.alias for e in CATALOG.values() if e.container}
    assert {"tts-kokoro", "tts-supertonic", "translator", "ollama"} <= aliases


def test_offline_lines_keep_what_the_parser_reads():
    raw = {
        "word": "lie", "pos": "verb", "lang_code": "en", "etymology_number": 2,
        "senses": [{"glosses": ["To be situated."], "examples": [{"text": "The town lies north."}, {"text": "x"}],
                    "categories": ["huge list"], "id": "en-lie-verb-1"}],
        "translations": [{"lang_code": "es", "word": "estar", "sense": "be situated", "roman": "-"},
                         {"lang_code": "de", "word": "liegen", "sense": "be situated"}],
        "forms": [{"form": "lay", "tags": ["past"], "source": "conjugation"}],
        "sounds": [{"ipa": "/laɪ/", "tags": ["US"]}, {"rhymes": "-aɪ"}],
        "head_templates": [{"name": "en-verb"}],
    }
    reduced = reduce_line(raw)
    assert "head_templates" not in reduced and "categories" not in reduced["senses"][0]
    assert [t["word"] for t in reduced["translations"]] == ["estar"]  # only meaning languages
    assert reduced["senses"][0]["examples"] == [{"text": "The town lies north."}]
    assert reduced["sounds"] == [{"ipa": "/laɪ/", "tags": ["US"]}]
    [entry] = parse_lines([reduced], "es")
    assert entry.translations[0].text == "estar" and entry.forms == ["lay"] and entry.etymology == 2
