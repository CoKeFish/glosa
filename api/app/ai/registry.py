"""Known AI providers. Adding one = one entry here plus a class implementing TextModel."""

import os
from dataclasses import dataclass
from typing import Callable

from app.ai.anthropic_provider import AnthropicTextModel
from app.ai.base import AINotConfigured, ModelConfig, TextModel
from app.ai.openai_compatible import OpenAICompatibleTextModel


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    label: str
    key_env: str | None  # API keys come from the environment (Doppler), never from the database
    default_model: str
    default_base_url: str | None
    base_url_editable: bool
    build: Callable[[ModelConfig, str | None], TextModel]


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
        ),
        ProviderSpec(
            id="openai",
            label="OpenAI",
            key_env="OPENAI_API_KEY",
            default_model="",
            default_base_url="https://api.openai.com/v1",
            base_url_editable=False,
            build=lambda cfg, key: OpenAICompatibleTextModel(
                cfg.model, "https://api.openai.com/v1", key, require_key=True, token_param="max_completion_tokens"
            ),
        ),
        ProviderSpec(
            id="openai_compatible",
            label="Compatible con OpenAI (Ollama, LM Studio, OpenRouter…)",
            key_env="OPENAI_COMPATIBLE_API_KEY",
            default_model="",
            default_base_url="http://host.docker.internal:11434/v1",
            base_url_editable=True,
            build=lambda cfg, key: OpenAICompatibleTextModel(cfg.model, cfg.base_url, key, require_key=False),
        ),
    ]
}

DEFAULT_TEXT_MODEL = ModelConfig(provider="anthropic", model="claude-opus-5-5")


def build_text_model(config: ModelConfig) -> TextModel:
    spec = PROVIDERS.get(config.provider)
    if spec is None:
        raise AINotConfigured(f"Proveedor desconocido: {config.provider}")
    key = os.environ.get(spec.key_env) if spec.key_env else None
    return spec.build(config, key or None)


def describe_providers() -> list[dict]:
    return [
        {
            "id": p.id,
            "label": p.label,
            "key_env": p.key_env,
            "key_configured": bool(p.key_env and os.environ.get(p.key_env)),
            "default_model": p.default_model,
            "default_base_url": p.default_base_url,
            "base_url_editable": p.base_url_editable,
        }
        for p in PROVIDERS.values()
    ]
