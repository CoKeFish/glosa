"""The hosted service: accounts by invitation, and every reader's data kept apart."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.db import SessionLocal
from app.main import app
from app.models import User

PASSWORD = "correct horse battery"


@pytest.fixture
def hosted(monkeypatch):
    monkeypatch.setenv("GLOSA_MODE", "hosted")
    monkeypatch.setenv("GLOSA_SECURE_COOKIES", "false")  # the test client speaks plain http
    auth._failures.clear()
    yield


def _email(tag: str) -> str:
    return f"{tag}-{uuid.uuid4().hex[:8]}@example.com"


def _admin_client() -> TestClient:
    email = _email("admin")
    with SessionLocal() as s:
        s.add(User(email=email, password_hash=auth.hash_password(PASSWORD), is_admin=True))
        s.commit()
    client = TestClient(app)
    assert client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200
    return client


def _reader(admin: TestClient, tag: str) -> TestClient:
    code = admin.post("/api/admin/invites", json={"note": tag}).json()["code"]
    client = TestClient(app)
    r = client.post("/api/auth/join", json={"code": code, "email": _email(tag), "password": PASSWORD})
    assert r.status_code == 200, r.text
    return client


def test_without_a_session_nothing_is_served(hosted):
    with TestClient(app) as client:
        assert client.get("/api/auth/me").json() == {"mode": "hosted", "user": None}
        for path in ("/api/books", "/api/settings", "/api/terms?language=en", "/api/languages",
                     "/api/dictionary?language=en&term=lie"):
            assert client.get(path).status_code == 401, path


def test_an_invitation_works_once(hosted):
    with TestClient(app):
        admin = _admin_client()
        invite = admin.post("/api/admin/invites", json={"note": "Ana"}).json()
        assert invite["url"].endswith(f"/join/{invite['code']}")
        assert TestClient(app).get(f"/api/auth/invites/{invite['code']}").json() == {"valid": True}
        first = TestClient(app).post("/api/auth/join", json={"code": invite["code"], "email": _email("ana"),
                                                             "password": PASSWORD})
        assert first.status_code == 200 and first.json()["user"]["is_admin"] is False
        again = TestClient(app).post("/api/auth/join", json={"code": invite["code"], "email": _email("eve"),
                                                             "password": PASSWORD})
        assert again.status_code == 400
        used = [i for i in admin.get("/api/admin/invites").json() if i["code"] == invite["code"]][0]
        assert used["used_by"].startswith("ana-")


def test_short_passwords_and_non_admins_are_refused(hosted):
    with TestClient(app):
        admin = _admin_client()
        code = admin.post("/api/admin/invites", json={}).json()["code"]
        r = TestClient(app).post("/api/auth/join", json={"code": code, "email": _email("bob"), "password": "short"})
        assert r.status_code == 400
        reader = _reader(admin, "carl")
        assert reader.post("/api/admin/invites", json={}).status_code == 403
        assert reader.get("/api/admin/users").status_code == 403


def test_readers_never_see_each_other(hosted):
    with TestClient(app):
        admin = _admin_client()
        ana, ben = _reader(admin, "ana"), _reader(admin, "ben")

        book = ana.post("/api/books/import", data={"language": "en", "title": "Ana's", "text": "The cat sat."}).json()
        assert [b["title"] for b in ana.get("/api/books").json()] == ["Ana's"]
        assert ben.get("/api/books").json() == []
        assert ben.get(f"/api/books/{book['id']}").status_code == 404
        assert ben.delete(f"/api/books/{book['id']}").status_code == 404
        section_id = ana.get(f"/api/books/{book['id']}").json()["sections"][0]["id"]
        assert ben.get(f"/api/sections/{section_id}").status_code == 404

        a_term = ana.put("/api/terms", json={"language": "en", "key": "cat", "meaning": "gato"}).json()
        ben.put("/api/terms", json={"language": "en", "key": "cat", "meaning": "felino"})
        assert [t["meaning"] for t in ben.get("/api/terms?language=en").json()["items"]] == ["felino"]
        assert ben.patch(f"/api/terms/{a_term['id']}", json={"meaning": "x"}).status_code == 404
        assert ana.get("/api/terms?language=en").json()["items"][0]["meaning"] == "gato"

        ana.put("/api/settings", json={"native_language": {"value": "fr"}})
        assert ana.get("/api/settings").json()["native_language"]["value"] == "fr"
        assert ben.get("/api/settings").json()["native_language"]["value"] == "es"


def test_wrong_passwords_are_throttled(hosted):
    with TestClient(app):
        email = _email("dana")
        with SessionLocal() as s:
            s.add(User(email=email, password_hash=auth.hash_password(PASSWORD)))
            s.commit()
        client = TestClient(app)
        codes = [client.post("/api/auth/login", json={"email": email, "password": "nope-nope-nope"}).status_code
                 for _ in range(9)]
        assert codes[:8] == [401] * 8 and codes[8] == 429


def test_logout_ends_the_session(hosted):
    with TestClient(app):
        reader = _reader(_admin_client(), "eli")
        assert reader.get("/api/books").status_code == 200
        reader.post("/api/auth/logout")
        assert reader.get("/api/books").status_code == 401


def test_hosted_service_has_no_docker_extras_and_refuses_other_origins(hosted):
    with TestClient(app):
        reader = _reader(_admin_client(), "fay")
        assert reader.get("/api/extras").status_code == 403
        assert reader.post("/api/extras-preset/light").status_code == 403
        r = reader.put("/api/terms", json={"language": "en", "key": "x"}, headers={"Origin": "https://evil.example"})
        assert r.status_code == 403


def test_the_public_address_counts_as_our_own_origin(hosted, monkeypatch):
    # Behind a proxy the API sees another Host; the configured public address is still ours.
    monkeypatch.setenv("GLOSA_PUBLIC_URL", "https://app.glosa.example")
    with TestClient(app):
        reader = _reader(_admin_client(), "gus")
        r = reader.put("/api/terms", json={"language": "en", "key": "y"}, headers={"Origin": "https://app.glosa.example"})
        assert r.status_code == 200
