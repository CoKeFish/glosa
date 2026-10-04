"""Sentence and phrase translation behind one interface.

Two providers: a local machine-translation server (LibreTranslate / Argos Translate,
no AI, works offline) and the configured AI model. Which one answers is a setting.
"""

import os
from typing import Protocol

import httpx

from app.ai import service as ai_service
from app.ai.base import TextModel


class TranslationError(Exception):
    pass


class Untranslated(TranslationError):
    """The translator answered with the source text unchanged."""


def _unchanged(source: str, result: str) -> bool:
    return result.strip().strip(".").lower() == source.strip().strip(".").lower()


class Translator(Protocol):
    id: str

    async def translate(self, text: str, source: str, target: str) -> str: ...


class LocalTranslator:
    id = "local"

    def __init__(self, url: str | None = None):
        self.url = (url or os.environ.get("TRANSLATOR_URL", "http://translator:5000")).rstrip("/")

    async def translate(self, text: str, source: str, target: str) -> str:
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


class AITranslator:
    id = "ai"

    def __init__(self, model: TextModel):
        self.model = model

    async def translate(self, text: str, source: str, target: str) -> str:
        return await ai_service.translate(self.model, language=source, native=target, text=text)
