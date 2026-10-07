import json
import random
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.drills import service
from app.drills.service import normalize_tag, parse_syllabus, plan_round, update_syllabus
from app.main import app
from app.models import Round, RoundItem, SyllabusTopic


def test_the_base_syllabus_has_every_block_and_topic_unseen():
    topics = parse_syllabus(service.BASE_SYLLABUS.read_text(encoding="utf-8"))
    assert len({t["block"] for t in topics}) == 18
    assert len(topics) == 86 and {t["status"] for t in topics} == {"no_visto"}


def test_markers_set_the_status():
    md = "## 2. Presente\n- 🟡 -s de tercera persona\n- 🟢 Presente continuo\n- ⬜ going to\n- sin marca\n"
    assert [(t["description"], t["status"]) for t in parse_syllabus(md)] == [
        ("-s de tercera persona", "falla"), ("Presente continuo", "dominado"), ("going to", "no_visto"),
        ("sin marca", "no_visto")]


def _topic(i, status, active=False):
    return SyllabusTopic(id=i, position=i, block="b", description=f"t{i}", status=status, active=active, streak=0)


def test_a_round_mixes_failing_active_and_review_topics():
    topics = [_topic(i, "falla") for i in range(1, 6)] + [_topic(6, "no_visto", active=True)] + \
             [_topic(i, "dominado") for i in range(7, 10)]
    slots = plan_round(topics, random.Random(0))
    kinds = [s.kind for s in slots]
    assert len(slots) == 7 and kinds.count("falla") == 3 and kinds.count("activo") == 2 and kinds.count("repaso") == 2
    assert all(t.id == 6 for s in slots if s.kind == "activo" for t in s.topics)


def test_a_new_syllabus_still_gets_seven_sentences():
    slots = plan_round([_topic(1, "no_visto", active=True), _topic(2, "no_visto")])
    assert len(slots) == 7


def _round(items):
    r = Round(id=1, user_id=1)
    r.items = [RoundItem(position=i, spanish="x", topic_ids=tids, failed_topic_ids=failed)
               for i, (tids, failed) in enumerate(items)]
    return r


def test_two_clean_rounds_master_a_topic_and_an_error_brings_it_back():
    topic = _topic(1, "falla")
    now = datetime.now(timezone.utc)
    update_syllabus(_round([([1], [])]), {1: topic}, now)
    assert (topic.status, topic.streak) == ("falla", 1)
    update_syllabus(_round([([1], [])]), {1: topic}, now)
    assert (topic.status, topic.streak) == ("dominado", 2)
    update_syllabus(_round([([1], [1])]), {1: topic}, now)
    assert (topic.status, topic.streak) == ("falla", 0)


def test_error_tags_are_normalized():
    assert normalize_tag("Tercera persona -s") == "tercera_persona_s"
    assert normalize_tag("Pasiva: falta «be»") == "pasiva_falta_be"
    assert normalize_tag("preposición_incorporada") == "preposicion_incorporada"


class FakeModel:
    """Writes the round and corrects it like a model would, from the prompts it receives."""

    model = "fake"
    last_usage = None

    def __init__(self):
        self.prompts = []

    async def complete(self, system, prompt, max_tokens=4000):
        self.prompts.append(prompt)
        if "Return exactly:\n{\"items\": [{\"slot\"" in prompt:
            return json.dumps({"items": [{"slot": n, "spanish": f"Frase número {n}."} for n in range(1, 8)]})
        topic_ids = [int(x) for x in __import__("re").findall(r"\[(\d+)\]", prompt)]
        items = [{"n": 1, "verdict": "con_errores", "correction": "She speaks English.",
                  "explanation": "Falta la -s de tercera persona.", "examples": ["He works here."],
                  "error_tags": ["Tercera persona -s"], "failed_topics": topic_ids[:1]}]
        items += [{"n": n, "verdict": "correcta", "correction": f"Answer {n}", "explanation": "Bien.",
                   "examples": [], "error_tags": [], "failed_topics": []} for n in range(2, 8)]
        return json.dumps({"items": items, "rules": [{"rule": "tercera persona: verbo + s", "example": "She speaks."}],
                           "vocabulary": [{"en": "confinement", "es": "encierro"}], "closing_note": "Bien en general."})


@pytest.fixture
def fake_ai(monkeypatch):
    model = FakeModel()
    monkeypatch.setattr("app.routers.drills._model", lambda session, user_id, override=None: model)
    return model


def test_a_whole_round(fake_ai):
    with TestClient(app) as client:
        assert len(client.get("/api/drills/syllabus").json()) > 0
        r = client.post("/api/drills/rounds", json={}).json()
        assert len(r["items"]) == 7 and r["items"][0]["spanish"] == "Frase número 1." and r["corrected_at"] is None

        done = client.post(f"/api/drills/rounds/{r['id']}/answers",
                           json={"answers": ["She speak English."] + [f"Answer {n}" for n in range(2, 8)]}).json()
        first = done["items"][0]
        assert first["verdict"] == "con_errores" and first["correction"] == "She speaks English."
        assert first["error_tags"] == ["tercera_persona_s"] and first["examples"] == ["He works here."]
        assert done["correct"] == 6 and done["closing_note"] == "Bien en general."

        again = client.post(f"/api/drills/rounds/{r['id']}/answers", json={"answers": [""] * 7})
        assert again.status_code == 502  # a corrected round is not corrected twice

        stats = client.get("/api/drills/stats").json()["errors"]
        assert {"tag": "tercera_persona_s", "count": 1} in stats
        failed = [t for t in client.get("/api/drills/syllabus").json() if t["id"] in first["failed_topic_ids"]]
        assert failed and all(t["status"] == "falla" for t in failed)

        terms = {t["key"]: t for t in client.get("/api/terms?language=en&q=").json()["items"]}
        assert terms["tercera persona: verbo + s"]["kind"] == "rule"
        assert terms["confinement"]["meaning"] == "encierro"
        assert client.get("/api/review/queue?language=en").status_code == 200

        apkg = client.get("/api/terms/export.apkg?language=en&tag=drills")
        assert apkg.status_code == 200 and apkg.content[:2] == b"PK"
        csv = client.get("/api/terms/export.csv?language=en&kind=rule").text
        assert "tercera persona: verbo + s" in csv and "confinement" not in csv


def test_without_an_ai_the_module_says_so(monkeypatch):
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    with TestClient(app) as client:
        client.put("/api/settings", json={"ai.text": {"provider": "anthropic", "model": "claude-opus-5-5"}})
        status = client.get("/api/drills/status").json()
        assert status["ready"] is False and status["reason"]
        assert client.post("/api/drills/rounds", json={}).status_code == 409


def test_prompts_are_files_the_reader_can_override():
    with TestClient(app) as client:
        prompts = client.get("/api/drills/prompts").json()
        assert prompts["corrector"]["custom"] is False and "---SYSTEM---" in prompts["corrector"]["text"]
        assert client.put("/api/drills/prompts/corrector", json={"text": "sin secciones"}).status_code == 400
        mine = "---SYSTEM---\nmine\n---PROMPT---\n{{items}}"
        client.put("/api/drills/prompts/corrector", json={"text": mine})
        assert client.get("/api/drills/prompts").json()["corrector"] == {
            "text": mine, "custom": True, "file": "api/app/drills/prompts/corrector.md"}
        client.put("/api/drills/prompts/corrector", json={"text": ""})  # back to the file
        assert client.get("/api/drills/prompts").json()["corrector"]["custom"] is False


def test_hosted_rounds_and_syllabus_belong_to_their_reader(fake_ai, monkeypatch):
    from tests.test_accounts import _admin_client, _reader

    monkeypatch.setenv("GLOSA_MODE", "hosted")
    monkeypatch.setenv("GLOSA_SECURE_COOKIES", "false")
    with TestClient(app):
        admin = _admin_client()
        ana, ben = _reader(admin, "ana"), _reader(admin, "ben")
        round_ = ana.post("/api/drills/rounds", json={}).json()
        assert ben.get(f"/api/drills/rounds/{round_['id']}").status_code == 404
        assert ben.post(f"/api/drills/rounds/{round_['id']}/answers", json={"answers": ["x"] * 7}).status_code == 404
        assert ben.get("/api/drills/rounds").json() == []
        a_topic = ana.get("/api/drills/syllabus").json()[0]
        assert ben.patch(f"/api/drills/syllabus/{a_topic['id']}", json={"status": "dominado"}).status_code == 404
        assert TestClient(app).get("/api/drills/rounds").status_code == 401
