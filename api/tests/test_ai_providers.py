"""Providers against a fake HTTP server: request shape and response handling, no real API calls."""

import asyncio
import json

import httpx
import httpx2  # the Anthropic SDK 1.x transport package
import pytest

from app.ai.anthropic_provider import AnthropicTextModel
from app.ai.base import AIError, AINotConfigured
from app.ai.openai_compatible import OpenAICompatibleTextModel
from app.translation import AITranslator


def anthropic_reply(text="apagar", stop_reason="end_turn"):
    return {
        "id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
        "content": [{"type": "text", "text": text}] if text else [],
        "stop_reason": stop_reason, "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 3},
    }


def fake_client(handler):
    return httpx2.AsyncClient(transport=httpx2.MockTransport(handler))


def test_anthropic_request_and_translation():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["headers"] = request.headers
        seen["body"] = json.loads(request.content)
        return httpx2.Response(200, json=anthropic_reply("Ella apagó la radio."))

    model = AnthropicTextModel("claude-opus-5-5", "sk-test", http_client=fake_client(handler))
    text = asyncio.run(AITranslator(model).translate("She turned the radio off.", "en", "es"))

    assert text == "Ella apagó la radio."
    assert seen["url"].endswith("/v1/messages?beta=true")
    assert seen["headers"]["x-api-key"] == "sk-test"
    assert "server-side-fallback-2026-07-01" in seen["headers"]["anthropic-beta"]
    body = seen["body"]
    assert body["model"] == "claude-opus-5-5"
    assert body["fallbacks"] == "default"
    assert body["output_config"] == {"effort": "low"}
    assert "Spanish" in body["system"]
    assert body["messages"] == [{"role": "user", "content": "She turned the radio off."}]


def test_anthropic_model_without_fallback_or_effort():
    seen = {}

    def handler(request):
        seen["url"], seen["body"] = str(request.url), json.loads(request.content)
        return httpx2.Response(200, json=anthropic_reply())

    model = AnthropicTextModel("claude-haiku-4-5", "sk-test", http_client=fake_client(handler))
    asyncio.run(model.complete("sys", "hi"))
    assert "beta" not in seen["url"]
    assert "output_config" not in seen["body"] and "fallbacks" not in seen["body"]


def test_anthropic_refusal_and_bad_key():
    model = AnthropicTextModel("claude-opus-5-5", "sk-test",
                               http_client=fake_client(lambda r: httpx2.Response(200, json=anthropic_reply(None, "refusal"))))
    with pytest.raises(AIError, match="rechazó"):
        asyncio.run(model.complete("sys", "hi"))

    unauthorized = httpx2.Response(401, json={"type": "error", "error": {"type": "authentication_error", "message": "invalid x-api-key"}})
    model = AnthropicTextModel("claude-opus-5-5", "sk-bad", http_client=fake_client(lambda r: unauthorized))
    with pytest.raises(AINotConfigured):
        asyncio.run(model.complete("sys", "hi"))


def test_model_list_drops_snapshots_and_non_chat(monkeypatch):
    from app.ai import openai_compatible

    data = {"data": [
        {"id": "gpt-5.5", "created": 3}, {"id": "gpt-5.5-2026-04-23", "created": 3},
        {"id": "text-embedding-3-large", "created": 2}, {"id": "sora-2", "created": 2}, {"id": "o4-mini", "created": 1},
    ]}

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            super().__init__(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=data)))

    monkeypatch.setattr("app.ai.openai_compatible.httpx.AsyncClient", FakeAsyncClient)
    models = asyncio.run(openai_compatible.list_models("https://api.openai.com/v1", "sk", chat_only=True))
    assert [m["id"] for m in models] == ["gpt-5.5", "o4-mini"]


def test_openai_compatible_request(monkeypatch):
    seen = {}

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            def handler(request):
                seen["url"], seen["body"] = str(request.url), json.loads(request.content)
                return httpx.Response(200, json={"choices": [{"message": {"content": "Buenos días"}}]})

            super().__init__(transport=httpx.MockTransport(handler))

    monkeypatch.setattr("app.ai.openai_compatible.httpx.AsyncClient", FakeAsyncClient)
    model = OpenAICompatibleTextModel("gemma3:4b", "http://host.docker.internal:11434/v1", None, require_key=False)
    assert asyncio.run(model.complete("sys", "Good morning")) == "Buenos días"
    assert seen["url"] == "http://host.docker.internal:11434/v1/chat/completions"
    assert seen["body"]["messages"][0] == {"role": "system", "content": "sys"}
    assert "max_tokens" in seen["body"]

    from app.ai.base import ModelConfig
    from app.ai.registry import build_text_model

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    openai_model = build_text_model(ModelConfig("openai", "gpt-5.5"))
    asyncio.run(openai_model.complete("sys", "hi"))
    assert "max_completion_tokens" in seen["body"] and "max_tokens" not in seen["body"]
