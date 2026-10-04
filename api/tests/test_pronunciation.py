from app.dictionary.kaikki import _sounds
from app.dictionary.ranking import Usage
from app.dictionary.service import _pronunciation

METAL = {"part_of_speech": "noun", "etymology": 1, "ipa": ["/ˈlɛd/"], "audio": [{"url": "metal.mp3", "accent": "US"}]}
METAL_VERB = {"part_of_speech": "verb", "etymology": 1, "ipa": [], "audio": []}
GUIDE_VERB = {"part_of_speech": "verb", "etymology": 2, "ipa": [], "audio": []}
GUIDE_NOUN = {"part_of_speech": "noun", "etymology": 2, "ipa": ["/ˈliːd/"], "audio": [{"url": "guide.mp3", "accent": "US"}]}
RESULTS = [{"term": "lead", "entries": [METAL, METAL_VERB, GUIDE_NOUN, GUIDE_VERB]}]


def test_pronunciation_follows_the_fitting_sense():
    guide = _pronunciation(RESULTS, Usage(pos="verb"), "lead", {"term": "lead", "etymology": 2})
    assert guide["ipa"] == ["/ˈliːd/"] and guide["audio"][0]["url"] == "guide.mp3"
    metal = _pronunciation(RESULTS, Usage(pos="noun"), "lead", {"term": "lead", "etymology": 1})
    assert metal["ipa"] == ["/ˈlɛd/"]


def test_no_pronunciation_borrowed_from_base_form():
    assert _pronunciation(RESULTS, Usage(pos="verb"), "led", {"term": "lead", "etymology": 2}) is None


def test_sounds_prefer_american_recordings():
    ipa, audio = _sounds([
        {"ipa": "/daʊt/"},
        {"audio": "uk.wav", "mp3_url": "uk.mp3", "tags": ["UK"]},
        {"audio": "us.ogg", "ogg_url": "us.ogg", "mp3_url": "us.mp3", "tags": ["General-American"]},
    ])
    assert ipa == ["/daʊt/"]
    assert [a["accent"] for a in audio] == ["US", "UK"]
