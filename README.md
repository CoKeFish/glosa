# glosa

> *Glosa* (Spanish): a gloss — the note that explains a word in a text.

Open source language learning by reading. Upload your own books, look up words as you read, and track the vocabulary you know.

## Why

Reading things you actually care about is one of the best ways to learn a language, and tools like [LingQ](https://www.lingq.com) are built around that idea. glosa is an open source take on it: your books, your data, no subscription.

## Status

Early development. You can import a book (EPUB, TXT, HTML) or paste text in English, read it with word statuses, phrasal verb and grammar detection, a dictionary and optional AI explanations, and review saved terms. Requirements live in [docs/requerimientos.md](docs/requerimientos.md).

## Running it

Everything runs in containers; you only need Docker.

```sh
docker compose up -d          # web on http://localhost:5174, API on http://localhost:8001
docker compose run --rm api pytest
```

AI features read their API keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`) from the environment, injected by [Doppler](https://www.doppler.com/) at start-up:

```sh
doppler run --project shared --config dev -- docker compose up -d
```

Keys can also be pasted under **Ajustes → Modelo de IA**; they are stored encrypted (Fernet) with a master key from `GLOSA_SECRET_KEY`, or one generated in the `api-data` volume. A key from the environment takes priority. Without any key, AI buttons report it and everything else (dictionary, local translator) keeps working. Pick the provider and model in the same place: Anthropic, OpenAI, DeepSeek, or any OpenAI-compatible server such as Ollama.

Pronunciation uses Wiktionary's recordings for single words and a local speech engine for everything else. Two engines run as containers and can be compared under **Ajustes → Voz**: Kokoro-82M (default, ~5 GB image) and Supertonic 3, which also covers the languages Kokoro lacks (German, Russian, Korean…). The browser's own voice is the last fallback.

Phrases and sentences are translated by default by a translation model running in [Ollama](https://ollama.com) on the host (`ollama pull translategemma:4b`), on the CPU unless the graphics card is enabled in **Ajustes → Traducción**. It reads the sentence around the selected fragment, so it picks the sense the fragment has there ("In relating" → "Al relatar"). If Ollama isn't running, a local LibreTranslate container translates instead (lighter, but it only sees the fragment); the paid AI can also be chosen. Every translation is cached in the database.

The dictionary is Wiktionary, through [Kaikki](https://kaikki.org): the English edition (translation tables, inflections, pronunciation) plus the edition written in the reader's language (Spanish, French, Portuguese or Italian), whose definitions fill the gaps of the English translation tables ("heaven" → "cielo, firmamento").

### Adding a language

Language-dependent logic lives in `api/app/languages/<code>/`: tokenizing, phrasal verbs, grammar rules and dictionaries. Write a pack that follows `api/app/languages/base.py` and register it in `api/app/languages/__init__.py`.

## Planned

- **Import your own books** and read them inside the app.
- **Look up words as you read** — select a word or phrase to see its meaning and save it.
- **Track what you know** — every word carries a status, so each page shows what is new, what you are learning and what you already know.
- **Review** the words you saved.

## Contributing

Ideas and feedback are welcome through issues while the design takes shape.

## License

[AGPL-3.0](LICENSE)
