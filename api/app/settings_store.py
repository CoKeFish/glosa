from sqlalchemy.orm import Session

from app import config
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


# The hosted service has no Ollama and no local translator: the AI translates, with a cheap
# model by default (DeepSeek v4 Flash, a fraction of a cent per phrase).
HOSTED_DEFAULTS = {
    "translation": {"provider": "ai", "llm_model": "translategemma:4b", "use_gpu": False},
    "ai.text": {"provider": "deepseek", "model": "deepseek-v4-flash", "base_url": None},
}


def default(key: str) -> dict:
    if config.hosted() and key in HOSTED_DEFAULTS:
        return HOSTED_DEFAULTS[key]
    return DEFAULTS.get(key, {})


def get(session: Session, user_id: int, key: str) -> dict:
    row = session.get(Setting, (user_id, key))
    return {**default(key), **(row.value if row else {})}


def put(session: Session, user_id: int, key: str, value: dict) -> dict:
    session.merge(Setting(user_id=user_id, key=key, value=value))
    session.commit()
    return get(session, user_id, key)


def all_settings(session: Session, user_id: int) -> dict:
    return {key: get(session, user_id, key) for key in DEFAULTS}


def native_language(session: Session, user_id: int) -> str:
    return get(session, user_id, "native_language")["value"]


def text_model_config(session: Session, user_id: int) -> ModelConfig:
    v = get(session, user_id, "ai.text")
    return ModelConfig(provider=v["provider"], model=v["model"], base_url=v.get("base_url"))
