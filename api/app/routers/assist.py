"""Languages, dictionaries, AI and settings."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import keystore, languages, settings_store
from app.ai import service as ai_service
from app.ai.base import AIError, AINotConfigured, ModelConfig
from app.ai.registry import PROVIDERS, build_text_model, describe_providers
from app.ai.registry import list_models as list_provider_models
from app.db import get_session
from app.dictionary import service as dictionary_service
from app.ai import pricing
from app import tts
from app.models import AIUsage, AudioCache, SpeechCache
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
    model = _model(session) if provider == "ai" else None
    translator = LocalTranslator() if model is None else AITranslator(model)
    try:
        text = await _run(translator.translate(body.text, body.language, native), session, model, "translate")
    except Untranslated as exc:
        # Not a failure of the service: tell the reader and let them ask the AI instead.
        return {"translation": None, "provider": translator.id, "message": str(exc)}
    except TranslationError as exc:
        raise HTTPException(502, str(exc))
    return {"translation": text, "provider": translator.id}


AUDIO_HOST = "https://upload.wikimedia.org/"
AUDIO_HEADERS = {"User-Agent": "glosa/0.1 (https://github.com/CoKeFish/glosa) python-httpx"}


@router.get("/audio")
async def audio(url: str, session: Session = Depends(get_session)):
    """Serve a pronunciation recording from Wikimedia Commons through the API: same origin for
    the browser, downloaded once, then available offline."""
    if not url.startswith(AUDIO_HOST):
        raise HTTPException(400, "Solo se sirven grabaciones de Wikimedia Commons")
    cached = session.get(AudioCache, url)
    if cached is None:
        try:
            async with httpx.AsyncClient(timeout=20, headers=AUDIO_HEADERS, follow_redirects=True) as client:
                resp = await client.get(url)
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"No se pudo descargar el audio: {exc}")
        if resp.status_code != 200:
            raise HTTPException(502, f"Wikimedia devolvió {resp.status_code}")
        cached = AudioCache(url=url, content=resp.content, content_type=resp.headers.get("content-type", "audio/mpeg"))
        session.merge(cached)
        session.commit()
    return Response(cached.content, media_type=cached.content_type,
                    headers={"Cache-Control": "public, max-age=31536000, immutable"})


@router.get("/tts/engines")
async def tts_engines(language: str = "en"):
    """Local speech engines, whether they are running, and their voices for the language."""
    result = []
    for engine in tts.ENGINES.values():
        try:
            voices = await tts.voices(engine.id, language)
            available = True
        except tts.TTSError:
            voices, available = [], False
        result.append({"id": engine.id, "label": engine.label, "available": available, "voices": voices,
                       "default_voice": tts.default_voice(engine.id, language)})
    return result


MAX_SPEECH_CHARS = 1000


@router.get("/tts")
async def speech(engine: str, text: str, language: str = "en", voice: str = "", nocache: bool = False,
                 session: Session = Depends(get_session)):
    """Speak `text` with a local engine. Cached per engine, voice and text; `nocache` measures
    the real synthesis time (used by the comparison in the settings)."""
    import hashlib

    if engine not in tts.ENGINES:
        raise HTTPException(400, f"Motor de voz desconocido: {engine}")
    # Kokoro has no German, Russian…: those go to Supertonic with its default voice.
    fallback = tts.engine_for(engine, language)
    if fallback != engine:
        engine, voice = fallback, ""
    text = text.strip()[:MAX_SPEECH_CHARS]
    if not text:
        raise HTTPException(400, "Texto vacío")
    voice = voice or tts.default_voice(engine, language)
    key = hashlib.sha256(f"{engine}|{voice}|{language}|{text}".encode()).hexdigest()
    cached = None if nocache else session.get(SpeechCache, key)
    if cached is None:
        try:
            content, media = await tts.synthesize(engine, voice, text, language)
        except tts.TTSError as exc:
            raise HTTPException(502, str(exc))
        cached = SpeechCache(key=key, content=content, content_type=media)
        session.merge(cached)
        session.commit()
    cache = "no-store" if nocache else "public, max-age=31536000, immutable"
    return Response(cached.content, media_type=cached.content_type, headers={"Cache-Control": cache})


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
def providers(session: Session = Depends(get_session)):
    return describe_providers(lambda p: keystore.stored_hint(session, p))


@router.get("/ai/models")
async def models(provider: str, base_url: str | None = None, session: Session = Depends(get_session)):
    """Models the configured key (or local server) offers, for the model dropdown."""
    items = await _run(list_provider_models(provider, base_url, lambda p: keystore.stored_key(session, p)))
    return {"models": items, "recommended": PROVIDERS[provider].default_model}


FEATURES = ("translate", "explain", "expressions", "grammar")


@router.get("/ai/usage")
def usage(days: int = 30, session: Session = Depends(get_session)):
    """What the AI cost over the last `days`, and what each feature costs per call with the
    model currently selected (from recorded usage, or typical sizes before there is any)."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func, select

    custom = settings_store.get(session, "ai.prices")
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = session.execute(
        select(AIUsage.provider, AIUsage.model, AIUsage.feature, func.count(),
               func.sum(AIUsage.input_tokens), func.sum(AIUsage.output_tokens))
        .where(AIUsage.at >= since)
        .group_by(AIUsage.provider, AIUsage.model, AIUsage.feature)
    ).all()

    total_cost, unpriced, calls = 0.0, 0, 0
    per_feature_tokens: dict[str, list[int]] = {}
    for provider, model, feature, n, tin, tout in rows:
        calls += n
        c = pricing.cost(int(tin or 0), int(tout or 0), pricing.price(provider, model, custom))
        if c is None:
            unpriced += n
        else:
            total_cost += c
        acc = per_feature_tokens.setdefault(feature, [0, 0, 0])
        acc[0] += n
        acc[1] += int(tin or 0)
        acc[2] += int(tout or 0)

    config = settings_store.text_model_config(session)
    current_price = pricing.price(config.provider, config.model, custom)
    features = []
    for feature in FEATURES:
        n, tin, tout = per_feature_tokens.get(feature, [0, 0, 0])
        measured = n > 0
        avg_in, avg_out = (tin / n, tout / n) if measured else pricing.TYPICAL_TOKENS[feature]
        features.append({
            "feature": feature,
            "calls": n,
            "measured": measured,
            "avg_input_tokens": round(avg_in),
            "avg_output_tokens": round(avg_out),
            "cost_per_call": pricing.cost(avg_in, avg_out, current_price),
        })
    return {
        "days": days,
        "calls": calls,
        "total_cost": round(total_cost, 4),
        "unpriced_calls": unpriced,
        "model": {"provider": config.provider, "model": config.model,
                  "price": {"input": current_price[0], "output": current_price[1]} if current_price else None,
                  "custom": config.model in custom},
        "features": features,
    }


class KeyIn(BaseModel):
    key: str


@router.put("/ai/keys/{provider}")
def save_key(provider: str, body: KeyIn, session: Session = Depends(get_session)):
    """Save an API key entered in the app. It is stored encrypted and never sent back."""
    if provider not in PROVIDERS:
        raise HTTPException(400, f"Proveedor desconocido: {provider}")
    if len(body.key.strip()) < 8:
        raise HTTPException(400, "La clave parece demasiado corta")
    keystore.save_key(session, provider, body.key)
    return {"ok": True}


@router.delete("/ai/keys/{provider}")
def delete_key(provider: str, session: Session = Depends(get_session)):
    keystore.delete_key(session, provider)
    return {"ok": True}


def _model(session: Session, override: ModelConfig | None = None):
    config = override or settings_store.text_model_config(session)
    try:
        model = build_text_model(config, lambda p: keystore.stored_key(session, p))
    except AINotConfigured as exc:
        raise HTTPException(409, str(exc))
    model.provider_id = config.provider  # for the usage log
    return model


async def _run(coro, session: Session | None = None, model=None, feature: str | None = None):
    """Await an AI call, map its errors to HTTP, and log its token usage when given the model."""
    try:
        result = await coro
    except AINotConfigured as exc:
        raise HTTPException(409, str(exc))
    except AIError as exc:
        raise HTTPException(502, str(exc))
    usage = getattr(model, "last_usage", None) if model is not None else None
    if session is not None and usage is not None and feature:
        session.add(AIUsage(provider=getattr(model, "provider_id", ""), model=model.model, feature=feature,
                            input_tokens=usage.input_tokens, output_tokens=usage.output_tokens))
        session.commit()
    return result


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
    ), session, model, "explain")


class TranslateIn(BaseModel):
    language: str
    text: str


@router.post("/ai/translate")
async def translate(body: TranslateIn, session: Session = Depends(get_session)):
    model = _model(session)
    text = await _run(ai_service.translate(
        model, language=body.language, native=settings_store.native_language(session), text=body.text
    ), session, model, "translate")
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
    ), session, model, "grammar")
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
    ), session, model, "expressions")
    return {"expressions": items}


class TestIn(BaseModel):
    provider: str
    model: str
    base_url: str | None = None


@router.post("/ai/test")
async def test_model(body: TestIn, session: Session = Depends(get_session)):
    """Try a configuration before saving it."""
    model = _model(session, ModelConfig(body.provider, body.model, body.base_url))
    text = await _run(ai_service.translate(model, language="en", native="es", text="Good morning"),
                      session, model, "test")
    return {"ok": True, "sample": text}
