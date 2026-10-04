import re

import httpx

from app.ai.base import AIError, AINotConfigured, Usage


# Models on OpenAI's /models that are not chat models.
NON_CHAT = ("embedding", "whisper", "tts", "dall-e", "image", "audio", "realtime", "transcribe", "moderation",
            "search", "davinci", "babbage", "computer-use", "codex", "sora", "instruct")


async def list_models(base_url: str | None, api_key: str | None, chat_only: bool) -> list[dict]:
    """Models served at base_url (/models), as {"id", "label"}."""
    if not base_url:
        raise AINotConfigured("Falta la URL base del servidor")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(base_url.rstrip("/") + "/models", headers=headers)
    except httpx.HTTPError as exc:
        raise AIError(f"No se pudo conectar con {base_url}") from exc
    if resp.status_code in (401, 403):
        raise AINotConfigured("La clave de API no es válida")
    if resp.status_code != 200:
        raise AIError(f"El servidor respondió {resp.status_code} al listar modelos")
    items = resp.json().get("data", [])
    ids = [m["id"] for m in items if isinstance(m, dict) and m.get("id")]
    if chat_only:
        ids = [i for i in ids if not any(word in i for word in NON_CHAT)]
    # Dated snapshots ("gpt-5.5-2026-04-23") duplicate their alias ("gpt-5.5"); keep the alias.
    ids = [i for i in ids if not (re.search(r"-\d{4}(-\d{2}-\d{2})?$", i) and re.sub(r"-\d{4}(-\d{2}-\d{2})?$", "", i) in ids)]
    created = {m["id"]: m.get("created", 0) for m in items if isinstance(m, dict) and m.get("id")}
    # Some providers send a readable name ("DeepSeek-V4.1-Flash"); show it next to the id.
    names = {m["id"]: m.get("name") for m in items if isinstance(m, dict) and m.get("id")}
    ids.sort(key=lambda i: created.get(i, 0), reverse=True)
    return [{"id": i, "label": f"{names[i]} ({i})" if names.get(i) and names[i] != i else i} for i in ids]


class OpenAICompatibleTextModel:
    """Any server speaking the OpenAI chat completions protocol: OpenAI, Ollama, LM Studio, OpenRouter, vLLM."""

    def __init__(self, model: str, base_url: str | None, api_key: str | None, require_key: bool,
                 token_param: str = "max_tokens"):
        # OpenAI's own API rejects max_tokens on current models and wants max_completion_tokens;
        # Ollama, LM Studio and most compatible servers still use max_tokens.
        self.token_param = token_param
        if not base_url:
            raise AINotConfigured("Falta la URL base del servidor")
        if require_key and not api_key:
            raise AINotConfigured("Falta la clave de API del proveedor")
        if not model:
            raise AINotConfigured("Falta el nombre del modelo")
        self.model = model
        self.last_usage: Usage | None = None
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    async def complete(self, system: str, prompt: str, max_tokens: int = 4000) -> str:
        body = {
            "model": self.model,
            self.token_param: max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        }
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(self.url, json=body, headers=self.headers)
        except httpx.HTTPError as exc:
            raise AIError(f"No se pudo conectar con {self.url}") from exc
        if resp.status_code in (401, 403):
            raise AINotConfigured("La clave de API no es válida")
        if resp.status_code != 200:
            raise AIError(f"El servidor respondió {resp.status_code}: {resp.text[:200]}")
        try:
            data = resp.json()
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, ValueError) as exc:
            raise AIError("Respuesta inesperada del servidor") from exc
        usage = data.get("usage") or {}
        self.last_usage = Usage(int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0)))
        return text
