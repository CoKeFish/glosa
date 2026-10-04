from fastapi.testclient import TestClient

from app import importers
from app.ai import registry
from app.ai.base import ModelConfig
from app.main import app


def test_split_long_keeps_paragraphs():
    text = "\n\n".join(["word " * 300] * 10)
    sections = importers.split_long("Ch", text, max_words=1000)
    assert len(sections) == 4
    assert all(len(s.text.split()) <= 1000 for s in sections)


def test_unknown_provider_is_rejected():
    import pytest
    from app.ai.base import AINotConfigured

    with pytest.raises(AINotConfigured):
        registry.build_text_model(ModelConfig("nope", "x"))


def test_missing_key_is_reported(monkeypatch):
    import pytest
    from app.ai.base import AINotConfigured

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(AINotConfigured):
        registry.build_text_model(ModelConfig("anthropic", "claude-opus-5-5"))


def test_import_read_and_save_flow():
    with TestClient(app) as client:
        r = client.post("/api/books/import", data={
            "language": "en", "title": "Test",
            "text": "She turned the radio off.\n\nThe cat looked after the kittens.",
        })
        assert r.status_code == 200, r.text
        book = client.get(f"/api/books/{r.json()['id']}").json()
        section = client.get(f"/api/sections/{book['sections'][0]['id']}").json()
        assert {u["k"] for u in section["units"]} >= {"turn off", "look after"}
        assert section["terms"] == {}

        saved = client.put("/api/terms", json={
            "language": "en", "key": "Turn  Off", "kind": "phrasal_verb", "meaning": "apagar",
        }).json()
        assert saved["key"] == "turn off" and saved["status"] == 1

        client.put("/api/terms", json={"language": "en", "key": "the radio", "kind": "phrase"})
        section = client.get(f"/api/sections/{book['sections'][0]['id']}").json()
        assert "turn off" in section["terms"]
        assert any(u["kind"] == "phrase" and u["k"] == "the radio" for u in section["units"])

        marked = client.post("/api/terms/mark-known", json={"language": "en", "keys": ["she", "cat"]}).json()
        assert marked["created"] == ["cat", "she"]
        assert client.post("/api/terms/undo-known", json={"language": "en", "keys": ["she", "cat"]}).json()["deleted"] == 2


def test_unsupported_language():
    with TestClient(app) as client:
        r = client.post("/api/books/import", data={"language": "xx", "text": "hola"})
        assert r.status_code == 400
