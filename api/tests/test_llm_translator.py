import asyncio

import httpx

from app.translation import LLMTranslator, TranslationError, clean_output, fragment_prompt


def test_fragment_prompt_includes_the_sentence():
    prompt = fragment_prompt("In relating", "en", "es", "In relating the circumstances which have led to my confinement")
    assert "In relating the circumstances" in prompt and '"In relating"' in prompt


def test_whole_sentence_is_translated_plainly():
    sentence = "It is an unfortunate fact."
    assert "Sentence:" not in fragment_prompt(sentence, "en", "es", sentence)


def test_clean_output_keeps_first_line_without_quotes():
    assert clean_output('"Al relatar"\n\nExplanation: …') == "Al relatar"


def test_cpu_by_default(monkeypatch):
    sent = {}

    async def post(self, url, json):
        sent.update(json)
        return httpx.Response(200, json={"message": {"content": "han llevado a"}})

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    assert asyncio.run(LLMTranslator().translate("led to", "en", "es", "which have led to my confinement")) == "han llevado a"
    assert sent["options"]["num_gpu"] == 0
    asyncio.run(LLMTranslator(use_gpu=True).translate("led to", "en", "es"))
    assert "num_gpu" not in sent["options"]


def test_answer_running_past_the_fragment_is_retried_alone(monkeypatch):
    answers = iter(["que están fuera de su experiencia común y corriente.", "estar fuera"])
    prompts = []

    async def post(self, url, json):
        prompts.append(json["messages"][0]["content"])
        return httpx.Response(200, json={"message": {"content": next(answers)}})

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    assert asyncio.run(LLMTranslator().translate("lie outside", "en", "es", "which lie outside its common experience")) == "estar fuera"
    assert "Sentence:" in prompts[0] and "Sentence:" not in prompts[1]


def test_ollama_down_is_a_translation_error(monkeypatch):
    async def post(self, url, json):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    try:
        asyncio.run(LLMTranslator().translate("led to", "en", "es"))
    except TranslationError as exc:
        assert "Ollama" in str(exc)
    else:
        raise AssertionError("expected TranslationError")
