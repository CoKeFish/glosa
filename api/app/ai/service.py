"""Language-learning tasks built on the TextModel interface. No provider code here."""

import json
import re

from app.ai.base import AIError, TextModel

LANGUAGE_NAMES = {"en": "English", "es": "Spanish", "fr": "French", "de": "German", "it": "Italian", "pt": "Portuguese"}

KIND_HINT = {
    "word": "a single word",
    "phrase": "a multi-word phrase",
    "phrasal_verb": "a phrasal verb (verb + particle/preposition, possibly separated in the sentence)",
}


def _name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code)


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise AIError("El modelo no devolvió JSON")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise AIError("El modelo devolvió JSON inválido") from exc


async def explain_term(model: TextModel, *, language: str, native: str, term: str, kind: str, context: str) -> dict:
    system = (
        f"You help a {_name(native)} speaker read {_name(language)}. "
        "Answer only with a JSON object, no prose around it."
    )
    prompt = (
        f"Term ({KIND_HINT.get(kind, 'a term')}): {term}\n"
        f"Sentence where it appears: {context}\n\n"
        "Return JSON with these keys:\n"
        f'- "translation": the meaning of the term in this sentence, in {_name(native)}, at most 6 words.\n'
        f'- "explanation": one or two sentences in {_name(native)} explaining the meaning and usage in this context.\n'
        '- "is_phrasal_verb": true if, in this sentence, the term works as a phrasal verb, false if the words are used literally.'
    )
    data = _parse_json(await model.complete(system, prompt))
    return {
        "translation": str(data.get("translation", "")).strip(),
        "explanation": str(data.get("explanation", "")).strip(),
        "is_phrasal_verb": bool(data.get("is_phrasal_verb", False)),
    }


async def explain_grammar(model: TextModel, *, language: str, native: str, sentence: str, structures: list[str]) -> str:
    system = (
        f"You are a patient {_name(language)} teacher for a {_name(native)} speaker. "
        f"Write in {_name(native)}, plain text, no markdown headings, at most 120 words."
    )
    listed = "\n".join(f"- {s}" for s in structures) or "- (none detected)"
    prompt = (
        f"Sentence: {sentence}\n\n"
        f"Structures a parser detected:\n{listed}\n\n"
        "Explain the grammar of this sentence for a learner: what each structure means here, "
        f"how to say it in {_name(native)}, and give the sentence's meaning. If the parser got something wrong, say so."
    )
    return (await model.complete(system, prompt)).strip()


async def find_expressions(model: TextModel, *, language: str, native: str, sentence: str,
                           known: list[str]) -> list[dict]:
    system = (
        f"You help a {_name(native)} speaker read {_name(language)}. "
        "Answer only with a JSON object, no prose around it."
    )
    already = ", ".join(known) or "none"
    prompt = (
        f"Sentence: {sentence}\n\n"
        "List the multi-word units in this sentence whose meaning a learner could not get word by word: "
        "idioms, fixed expressions, phrasal verbs, prepositional verbs and strong collocations. "
        f"Skip these, already marked: {already}. Skip ordinary free combinations.\n\n"
        'Return {"expressions": [...]} where each item has:\n'
        '- "text": the words exactly as they appear in the sentence (same spelling and order; may skip words in between only for separated phrasal verbs, joined with " ... ")\n'
        "- \"base\": the dictionary form (infinitive verb, \"one's\" for possessives), lowercase\n"
        f'- "meaning": its meaning here, in {_name(native)}, at most 6 words\n'
        "Return an empty list if there are none."
    )
    data = _parse_json(await model.complete(system, prompt))
    items = data.get("expressions", []) if isinstance(data, dict) else []
    result = []
    for item in items:
        if isinstance(item, dict) and item.get("text") and item.get("base"):
            result.append({
                "text": str(item["text"]).strip(),
                "base": str(item["base"]).strip().lower(),
                "meaning": str(item.get("meaning", "")).strip(),
            })
    return result


language_name = _name


async def translate(model: TextModel, *, language: str, native: str, text: str, context: str = "") -> str:
    system = f"Translate {_name(language)} to {_name(native)}. Reply with the translation only."
    if context and text.strip() != context.strip():
        # Without the sentence, "In relating" reads as "Al relacionar"; with it, "Al relatar".
        prompt = (f"Sentence: {context}\n\nTranslate only this fragment, with the meaning it has in that "
                  f"sentence: \"{text}\"")
        return (await model.complete(system, prompt)).strip().strip('"')
    return (await model.complete(system, text)).strip()
