import anthropic

from app.ai.base import AIError, AINotConfigured

# Models that accept output_config.effort; Haiku 4.5 and older reject it.
EFFORT_PREFIXES = ("claude-fable", "claude-mythos", "claude-opus-5", "claude-opus-4-8", "claude-opus-4-7",
                   "claude-opus-4-6", "claude-sonnet-5", "claude-sonnet-4-6")
# Models where the API can retry a refused request on another model.
FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5"}


class AnthropicTextModel:
    def __init__(self, model: str, api_key: str | None, http_client=None):
        if not api_key:
            raise AINotConfigured("Falta la variable de entorno ANTHROPIC_API_KEY")
        self.model = model
        self.client = anthropic.AsyncAnthropic(api_key=api_key, http_client=http_client, max_retries=0)

    async def complete(self, system: str, prompt: str, max_tokens: int = 4000) -> str:
        params = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.model.startswith(EFFORT_PREFIXES):
            # Glosses are short; low effort keeps them fast and cheap.
            params["output_config"] = {"effort": "low"}
        try:
            if self.model in FALLBACK_MODELS:
                response = await self.client.beta.messages.create(
                    **params, betas=["server-side-fallback-2026-07-01"], fallbacks="default"
                )
            else:
                response = await self.client.messages.create(**params)
        except anthropic.AuthenticationError as exc:
            raise AINotConfigured("ANTHROPIC_API_KEY no es válida") from exc
        except anthropic.NotFoundError as exc:
            raise AIError(f"Modelo desconocido: {self.model}") from exc
        except anthropic.RateLimitError as exc:
            raise AIError("Límite de uso alcanzado; prueba en un momento") from exc
        except anthropic.APIStatusError as exc:
            raise AIError(f"Error de Anthropic ({exc.status_code}): {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise AIError("No se pudo conectar con Anthropic") from exc

        if response.stop_reason == "refusal":
            raise AIError("El modelo rechazó la petición")
        return "".join(block.text for block in response.content if block.type == "text")
