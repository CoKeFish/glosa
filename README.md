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

AI features read their API keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) from the environment, injected by [Doppler](https://www.doppler.com/) at start-up:

```sh
doppler run --project shared --config dev -- docker compose up -d
```

A plain `docker compose up` starts the app without keys; AI buttons then report the missing key, and everything else (dictionary, local translator) keeps working. Pick the provider and model under **Ajustes**: Anthropic, OpenAI, or any OpenAI-compatible server such as Ollama.

Phrases and sentences are translated by a local LibreTranslate container by default (no AI, works offline after its first start downloads the models); the AI can be chosen instead in **Ajustes**.

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
