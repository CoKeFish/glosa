"""Languages, dictionaries, AI and settings."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import languages, settings_store
from app.ai import service as ai_service
from app.ai.base import AIError, AINotConfigured, ModelConfig
from app.ai.registry import PROVIDERS, build_text_model, describe_providers
from app.db import get_session
from app.dictionary import service as dictionary_service
from app.routers.common import require_language
from app.translation import AITranslator, LocalTranslator, TranslationError, Untranslated

router = APIRouter(prefix="/api")


@router.get("/languages")
def list_languages():
    return languages.available()


@router.get("/dictionary")
async def lookup(language: str, term: str, lemma: str | None = None, context: str = "", surface: str | None = None,
                 kind: str = "word", session: Session = Depends(get_session)):
    """`context` is the sentence the word is in; translations are ranked against it."""
    require_language(language)
    terms = [term] + ([lemma] if lemma else [])
    return await dictionary_service.lookup(
        session, language, terms, settings_store.native_language(session),
        context=context, surface=surface, kind=kind,
    )


class TranslateTextIn(BaseModel):
    language: str
    text: str
    provider: str | None = None  # "local" or "ai"; defaults to the setting


@router.post("/translate")
async def translate_text(body: TranslateTextIn, session: Session = Depends(get_session)):
    """Translate a phrase or sentence with the configured translator, or the one asked for."""
    native = settings_store.native_language(session)
    provider = body.provider or settings_store.get(session, "translation")["provider"]
    if provider not in ("local", "ai"):
        raise HTTPException(400, f"Traductor desconocido: {provider}")
    translator = LocalTranslator() if provider == "local" else AITranslator(_model(session))
    try:
        text = await _run(translator.translate(body.text, body.language, native))
    except Untranslated as exc:
        # Not a failure of the service: tell the reader and let them ask the AI instead.
        return {"translation": None, "provider": translator.id, "message": str(exc)}
    except TranslationError as exc:
        raise HTTPException(502, str(exc))
    return {"translation": text, "provider": translator.id}


@router.get("/settings")
def get_settings(session: Session = Depends(get_session)):
    return settings_store.all_settings(session)


@router.put("/settings")
def put_settings(body: dict[str, dict], session: Session = Depends(get_session)):
    for key, value in body.items():
        if key not in settings_store.DEFAULTS:
            raise HTTPException(400, f"Ajuste desconocido: {key}")
        if key == "ai.text" and value.get("provider") not in PROVIDERS:
            raise HTTPException(400, f"Proveedor desconocido: {value.get('provider')}")
        settings_store.put(session, key, value)
    return settings_store.all_settings(session)


@router.get("/ai/providers")
def providers():
    return describe_providers()


def _model(session: Session, override: ModelConfig | None = None):
    try:
        return build_text_model(override or settings_store.text_model_config(session))
    except AINotConfigured as exc:
        raise HTTPException(409, str(exc))


async def _run(coro):
    try:
        return await coro
    except AINotConfigured as exc:
        raise HTTPException(409, str(exc))
    except AIError as exc:
        raise HTTPException(502, str(exc))


class ExplainIn(BaseModel):
    language: str
    term: str
    kind: str = "word"
    context: str = ""


@router.post("/ai/explain")
async def explain(body: ExplainIn, session: Session = Depends(get_session)):
    model = _model(session)
    return await _run(ai_service.explain_term(
        model, language=body.language, native=settings_store.native_language(session),
        term=body.term, kind=body.kind, context=body.context,
    ))


class TranslateIn(BaseModel):
    language: str
    text: str


@router.post("/ai/translate")
async def translate(body: TranslateIn, session: Session = Depends(get_session)):
    model = _model(session)
    text = await _run(ai_service.translate(
        model, language=body.language, native=settings_store.native_language(session), text=body.text
    ))
    return {"translation": text}


class GrammarIn(BaseModel):
    language: str
    sentence: str
    structures: list[str] = []


@router.post("/ai/grammar")
async def grammar(body: GrammarIn, session: Session = Depends(get_session)):
    model = _model(session)
    text = await _run(ai_service.explain_grammar(
        model, language=body.language, native=settings_store.native_language(session),
        sentence=body.sentence, structures=body.structures,
    ))
    return {"explanation": text}


class ExpressionsIn(BaseModel):
    language: str
    sentence: str
    known: list[str] = []


@router.post("/ai/expressions")
async def find_expressions(body: ExpressionsIn, session: Session = Depends(get_session)):
    """Expressions the automatic detection missed, found by the AI in one sentence."""
    model = _model(session)
    items = await _run(ai_service.find_expressions(
        model, language=body.language, native=settings_store.native_language(session),
        sentence=body.sentence, known=body.known,
    ))
    return {"expressions": items}


class TestIn(BaseModel):
    provider: str
    model: str
    base_url: str | None = None


@router.post("/ai/test")
async def test_model(body: TestIn, session: Session = Depends(get_session)):
    """Try a configuration before saving it."""
    model = _model(session, ModelConfig(body.provider, body.model, body.base_url))
    text = await _run(ai_service.translate(model, language="en", native="es", text="Good morning"))
    return {"ok": True, "sample": text}
