from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import ApiKey


def test_saved_key_is_encrypted_and_never_returned(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with TestClient(app) as client:
        assert client.put("/api/ai/keys/openai", json={"key": "sk-test-1234567890abcd"}).status_code == 200

        with SessionLocal() as s:
            row = s.get(ApiKey, "openai")
            assert "sk-test" not in row.encrypted and row.hint == "abcd"

        providers = {p["id"]: p for p in client.get("/api/ai/providers").json()}
        assert providers["openai"]["key_source"] == "saved"
        assert providers["openai"]["key_hint"] == "abcd"
        assert "sk-test" not in str(providers)

        assert client.delete("/api/ai/keys/openai").status_code == 200
        providers = {p["id"]: p for p in client.get("/api/ai/providers").json()}
        assert providers["openai"]["key_configured"] is False


def test_environment_key_wins(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    with TestClient(app) as client:
        client.put("/api/ai/keys/openai", json={"key": "sk-saved-in-app-0000"})
        p = {p["id"]: p for p in client.get("/api/ai/providers").json()}["openai"]
        assert p["key_source"] == "env" and p["key_hint"] is None
        client.delete("/api/ai/keys/openai")


def test_saved_key_is_used_by_the_provider(monkeypatch):
    from app import keystore
    from app.ai.base import ModelConfig
    from app.ai.registry import build_text_model

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with SessionLocal() as s:
        keystore.save_key(s, "openai", "sk-saved-key-9999")
        model = build_text_model(ModelConfig("openai", "gpt-5.5"), lambda p: keystore.stored_key(s, p))
        assert model.headers["Authorization"] == "Bearer sk-saved-key-9999"
        keystore.delete_key(s, "openai")
