from app.tts import default_voice, engine_for


def test_kokoro_languages_stay_on_kokoro():
    assert engine_for("kokoro", "en") == "kokoro"
    assert engine_for("kokoro", "es") == "kokoro"


def test_languages_kokoro_lacks_fall_back_to_supertonic():
    assert engine_for("kokoro", "de") == "supertonic"
    assert engine_for("kokoro", "ru") == "supertonic"
    assert default_voice("supertonic", "de") == "F1"


def test_chosen_engine_is_respected_when_it_speaks_the_language():
    assert engine_for("supertonic", "en") == "supertonic"
