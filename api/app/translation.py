"""Sentence and phrase translation behind one interface.

Three providers, chosen in the settings:
- "llm": a translation model running locally in Ollama (TranslateGemma by default). Free,
  offline, and it reads the whole sentence to translate a fragment in context. Runs on the
  CPU unless the reader enables the graphics card.
- "local": a machine-translation server (LibreTranslate / Argos Translate). Lighter, but it
  only sees the fragment, so short pieces come out literal ("lie outside" → "miente afuera").
- "ai": the configured AI model (paid per request).
"""

import os
import re
from typing import Protocol

import httpx

from app.ai import service as ai_service
from app.ai.base import TextModel
from app.ai.service import language_name


class TranslationError(Exception):
    pass


class Untranslated(TranslationError):
    """The translator answered with the source text unchanged."""


def _unchanged(source: str, result: str) -> bool:
    return result.strip().strip(".").lower() == source.strip().strip(".").lower()


class Translator(Protocol):
    id: str
    uses_context: bool  # whether the sentence around the text changes the translation

    async def translate(self, text: str, source: str, target: str, context: str = "") -> str: ...


class LocalTranslator:
    id = "local"
    uses_context = False

    def __init__(self, url: str | None = None):
        self.url = (url or os.environ.get("TRANSLATOR_URL", "http://translator:5000")).rstrip("/")

    async def translate(self, text: str, source: str, target: str, context: str = "") -> str:
        result = (await self.translate_many([text], source, target))[0]
        # Argos echoes short capitalised fragments untouched ("In relating" → "In relating")
        # but translates them in lower case ("in relating" → "en relación con").
        if _unchanged(text, result) and text[:1].isupper():
            retry = (await self.translate_many([text[0].lower() + text[1:]], source, target))[0]
            if not _unchanged(text, retry):
                result = retry[0].upper() + retry[1:]
        if _unchanged(text, result):
            raise Untranslated("El traductor local no pudo traducir este fragmento")
        return result

    async def translate_many(self, texts: list[str], source: str, target: str) -> list[str]:
        """One request for several short texts (LibreTranslate accepts a list)."""
        body = {"q": texts, "source": source, "target": target, "format": "text"}
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{self.url}/translate", json=body)
        except httpx.HTTPError as exc:
            raise TranslationError("El traductor local no responde (¿sigue descargando modelos?)") from exc
        if resp.status_code != 200:
            try:
                detail = resp.json().get("error", resp.text)
            except ValueError:
                detail = resp.text
            raise TranslationError(f"Traductor local: {detail}")
        return [t.strip() for t in resp.json()["translatedText"]]


def fragment_prompt(text: str, source: str, target: str, context: str = "") -> str:
    """Prompt for a translation model. With the sentence around it, the model picks the sense
    the fragment has there ("In relating" → "Al relatar", not "Al relacionar")."""
    src, tgt = language_name(source), language_name(target)
    if context and text.strip() != context.strip():
        return (f"Sentence: {context}\n\nTranslate into {tgt} only this fragment of the {src} sentence, "
                f"as it is used there: \"{text}\"\nOutput only the {tgt} translation of the fragment.")
    return f"Translate the following {src} text into {tgt}. Output only the translation.\n\n{text}"


def clean_output(answer: str) -> str:
    """First line of the answer, without the quotes models like to add."""
    line = next((ln for ln in answer.strip().splitlines() if ln.strip()), "")
    return re.sub(r'^["«“]+|["»”]+$', "", line.strip()).strip()


OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434").rstrip("/")
DEFAULT_LLM = "translategemma:4b"


class LLMTranslator:
    """A translation model served by Ollama. On the CPU by default: a phrase takes well under a
    second on a desktop processor and the graphics card stays free."""

    id = "llm"
    uses_context = True

    def __init__(self, model: str = DEFAULT_LLM, use_gpu: bool = False, url: str | None = None,
                 keep_alive: str = "5m"):
        self.model, self.use_gpu, self.keep_alive = model, use_gpu, keep_alive
        self.url = (url or OLLAMA_URL).rstrip("/")

    async def translate(self, text: str, source: str, target: str, context: str = "") -> str:
        result = await self._ask(fragment_prompt(text, source, target, context))
        # With the sentence in view the model sometimes runs on past the fragment ("lie outside"
        # → "que están fuera de la experiencia común"). Far too long: translate the fragment alone.
        if context and len(result.split()) > max(4, 3 * len(text.split())):
            result = await self._ask(fragment_prompt(text, source, target))
        return result

    async def _ask(self, prompt: str) -> str:
        body = {
            "model": self.model, "stream": False, "keep_alive": self.keep_alive,
            # num_gpu is how many layers go to the graphics card: 0 keeps it all on the CPU.
            "options": {"temperature": 0, **({} if self.use_gpu else {"num_gpu": 0})},
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(f"{self.url}/api/chat", json=body)
        except httpx.HTTPError as exc:
            raise TranslationError("El modelo local no responde: ¿está Ollama en marcha?") from exc
        if resp.status_code != 200:
            raise TranslationError(f"Modelo local: {resp.json().get('error', resp.text)[:200]}")
        result = clean_output(resp.json()["message"]["content"])
        if not result:
            raise Untranslated("El modelo local no devolvió traducción")
        return result


async def llm_models(url: str | None = None) -> list[str]:
    """Models installed in Ollama; empty if Ollama is not running."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            data = (await client.get(f"{(url or OLLAMA_URL).rstrip('/')}/api/tags")).json()
    except (httpx.HTTPError, ValueError):
        return []
    return sorted(m["name"] for m in data.get("models", []) if "embed" not in m["name"])


class AITranslator:
    id = "ai"
    uses_context = True

    def __init__(self, model: TextModel):
        self.model = model

    async def translate(self, text: str, source: str, target: str, context: str = "") -> str:
        return await ai_service.translate(self.model, language=source, native=target, text=text, context=context)
