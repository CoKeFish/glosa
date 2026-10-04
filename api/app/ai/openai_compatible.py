import httpx

from app.ai.base import AIError, AINotConfigured


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
            return resp.json()["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, ValueError) as exc:
            raise AIError("Respuesta inesperada del servidor") from exc
