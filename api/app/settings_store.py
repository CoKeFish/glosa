from sqlalchemy.orm import Session

from app.ai.base import ModelConfig
from app.ai.registry import DEFAULT_TEXT_MODEL
from app.models import Setting

DEFAULTS = {
    # Three languages, like LingQ: the interface's, the one meanings and explanations are
    # written in (native_language), and the one being studied (per book, chosen in the app).
    "ui_language": {"value": "es"},
    "native_language": {"value": "es"},
    # click_saves: clicking a new word means you don't know it, so it is saved as status 1
    # (LingQ's "Auto LingQ creation").
    # auto_play: pronounce whatever is selected (LingQ's "Auto play text-to-speech").
    "reader": {"page_marks_known": True, "click_saves": True, "auto_play": True},
    "review": {"session_size": 20},
    # Voice for pronunciation: "browser" or a local engine (kokoro, supertonic, piper);
    # voices maps "engine:language" to the chosen voice.
    # prefer_recordings: for single words, play Wiktionary's human recordings when they exist.
    "tts": {"engine": "kokoro", "voices": {}, "prefer_recordings": True},
    # Who translates phrases and sentences: "llm" (a translation model in Ollama, reads the
    # sentence around the fragment), "local" (LibreTranslate) or "ai". The model runs on the
    # CPU unless use_gpu; if Ollama does not answer, LibreTranslate translates instead.
    "translation": {"provider": "llm", "llm_model": "translategemma:4b", "use_gpu": False},
    "ai.text": {"provider": DEFAULT_TEXT_MODEL.provider, "model": DEFAULT_TEXT_MODEL.model, "base_url": None},
    # Prices the reader entered for models without a known price: {model: {"input", "output"}} in USD/M tokens.
    "ai.prices": {},
}


def get(session: Session, key: str) -> dict:
    row = session.get(Setting, key)
    return {**DEFAULTS.get(key, {}), **(row.value if row else {})}


def put(session: Session, key: str, value: dict) -> dict:
    session.merge(Setting(key=key, value=value))
    session.commit()
    return get(session, key)


def all_settings(session: Session) -> dict:
    return {key: get(session, key) for key in DEFAULTS}


def native_language(session: Session) -> str:
    return get(session, "native_language")["value"]


def text_model_config(session: Session) -> ModelConfig:
    v = get(session, "ai.text")
    return ModelConfig(provider=v["provider"], model=v["model"], base_url=v.get("base_url"))
