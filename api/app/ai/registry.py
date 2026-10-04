"""Known AI providers. Adding one = one entry here plus a class implementing TextModel."""

import os
from dataclasses import dataclass
from typing import Awaitable, Callable

from app.ai import anthropic_provider, openai_compatible
from app.ai.anthropic_provider import AnthropicTextModel
from app.ai.base import AINotConfigured, ModelConfig, TextModel
from app.ai.openai_compatible import OpenAICompatibleTextModel

OPENAI_URL = "https://api.openai.com/v1"
DEEPSEEK_URL = "https://api.deepseek.com"  # OpenAI-compatible


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    label: str
    key_env: str | None  # environment variable with the key; a key saved in the app is the fallback
    default_model: str  # recommended model, preselected in the model list
    default_base_url: str | None
    base_url_editable: bool
    build: Callable[[ModelConfig, str | None], TextModel]
    # (key, base_url) → models the key/server offers, as {"id", "label"}
    list_models: Callable[[str | None, str | None], Awaitable[list[dict]]]


PROVIDERS: dict[str, ProviderSpec] = {
    p.id: p
    for p in [
        ProviderSpec(
            id="anthropic",
            label="Anthropic (Claude)",
            key_env="ANTHROPIC_API_KEY",
            default_model="claude-opus-5-5",
            default_base_url=None,
            base_url_editable=False,
            build=lambda cfg, key: AnthropicTextModel(cfg.model, key),
            list_models=lambda key, _url: anthropic_provider.list_models(key),
        ),
        ProviderSpec(
            id="openai",
            label="OpenAI",
            key_env="OPENAI_API_KEY",
            default_model="gpt-5.5",
            default_base_url=OPENAI_URL,
            base_url_editable=False,
            build=lambda cfg, key: OpenAICompatibleTextModel(
                cfg.model, OPENAI_URL, key, require_key=True, token_param="max_completion_tokens"
            ),
            list_models=lambda key, _url: openai_compatible.list_models(OPENAI_URL, key, chat_only=True),
        ),
        ProviderSpec(
            id="deepseek",
            label="DeepSeek",
            key_env="DEEPSEEK_API_KEY",
            default_model="deepseek-flash",
            default_base_url=DEEPSEEK_URL,
            base_url_editable=False,
            build=lambda cfg, key: OpenAICompatibleTextModel(cfg.model, DEEPSEEK_URL, key, require_key=True),
            list_models=lambda key, _url: openai_compatible.list_models(DEEPSEEK_URL, key, chat_only=True),
        ),
        ProviderSpec(
            id="openai_compatible",
            label="Compatible con OpenAI (Ollama, LM Studio, OpenRouter…)",
            key_env="OPENAI_COMPATIBLE_API_KEY",
            default_model="",
            default_base_url="http://host.docker.internal:11434/v1",
            base_url_editable=True,
            build=lambda cfg, key: OpenAICompatibleTextModel(cfg.model, cfg.base_url, key, require_key=False),
            list_models=lambda key, url: openai_compatible.list_models(url, key, chat_only=True),
        ),
    ]
}

DEFAULT_TEXT_MODEL = ModelConfig(provider="anthropic", model="claude-opus-5-5")


def _key(spec: ProviderSpec, stored_key: Callable[[str], str | None]) -> str | None:
    return (os.environ.get(spec.key_env) if spec.key_env else None) or stored_key(spec.id) or None


def build_text_model(config: ModelConfig, stored_key: Callable[[str], str | None] = lambda _: None) -> TextModel:
    """`stored_key(provider)` returns a key saved in the app; the environment wins over it."""
    spec = PROVIDERS.get(config.provider)
    if spec is None:
        raise AINotConfigured(f"Proveedor desconocido: {config.provider}")
    return spec.build(config, _key(spec, stored_key))


async def list_models(provider: str, base_url: str | None,
                      stored_key: Callable[[str], str | None] = lambda _: None) -> list[dict]:
    spec = PROVIDERS.get(provider)
    if spec is None:
        raise AINotConfigured(f"Proveedor desconocido: {provider}")
    return await spec.list_models(_key(spec, stored_key), base_url or spec.default_base_url)


def describe_providers(stored_hint: Callable[[str], str | None] = lambda _: None) -> list[dict]:
    result = []
    for p in PROVIDERS.values():
        from_env = bool(p.key_env and os.environ.get(p.key_env))
        hint = stored_hint(p.id)
        result.append({
            "id": p.id,
            "label": p.label,
            "key_env": p.key_env,
            "key_configured": from_env or hint is not None,
            # "env" (Doppler/environment, takes priority), "saved" (entered in the app) or None
            "key_source": "env" if from_env else ("saved" if hint is not None else None),
            "key_hint": None if from_env else hint,
            "default_model": p.default_model,
            "default_base_url": p.default_base_url,
            "base_url_editable": p.base_url_editable,
        })
    return result
