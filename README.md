# glosa

> *Glosa* (Spanish): a gloss — the note that explains a word in a text.

Open source language learning by reading. Upload your own books, look up words as you read, and track the vocabulary you know.

## Why

Reading things you actually care about is one of the best ways to learn a language, and tools like [LingQ](https://www.lingq.com) are built around that idea. glosa is an open source take on it: your books, your data, no subscription.

## Status

Early development. You can import a book (EPUB, TXT, HTML) or paste text in English, read it with word statuses, phrasal verb and grammar detection, a dictionary and optional AI explanations, and review saved terms. Requirements live in [docs/requerimientos.md](docs/requerimientos.md).

## Installing

**Windows:** download `glosa-setup-<version>.exe` from [Releases](https://github.com/CoKeFish/glosa/releases) and run it. It installs Docker Desktop if it is missing, asks for a **Light** (about 2 GB of extras) or **Recommended** (about 10 GB) setup, and adds glosa to the Start menu and desktop. The app opens at http://localhost:7878. Uninstalling asks whether to keep your books and vocabulary.

**Other systems:** with Docker installed, copy [`installer/compose.yaml`](installer/compose.yaml) and run `docker compose -p glosa up -d`.

### Extras

The core (database, API, web) is small. Everything heavy is an extra, installed and removed from the app's **Extras** page, one by one or as the Light / Recommended sets:

| Extra | Size | What it gives |
|---|---|---|
| Local translation model (TranslateGemma in Ollama) | ~3.3 GB (+3.5 GB if no Ollama on the host) | translations that read the sentence |
| Basic translator (LibreTranslate) | ~1.3 GB | light fallback translator |
| Kokoro voice | ~5 GB | the most natural voice |
| Supertonic voice | ~0.9 GB | light voice, 31 languages |
| Offline dictionary | 0.5 GB download, ~0.7 GB stored | all of Wiktionary, no internet needed |

The app reaches Docker through its socket to do this, and only touches containers it labelled `glosa.extra`. API keys for cloud AI can be entered on the same page; they are stored encrypted on that computer only.

### Practice (Drills)

The **Práctica** page adds guided practice to reading: rounds of 7 sentences in Spanish to translate into English, corrected by the configured AI (it needs one; nothing is corrected by local rules). Each round mixes 2-3 topics you get wrong, 2 of the topic you are learning and 2 mastered ones for review, from a syllabus (`api/app/drills/temario-base.md` by default, or your own `temario.md` imported from the page, with ⬜ 🟡 🟢 markers). The correction shows what changed, explains every mistake, tags it, moves the syllabus (🟡 → 🟢 after two clean rounds in a row, back to 🟡 when the mistake returns) and sends rules and new words to the review queue, exportable to Anki (`.apkg` or CSV). The prompts are files, `api/app/drills/prompts/generator.md` and `corrector.md`, read on every round; you can also save your own version from the page.

### Self-hosted or hosted

One codebase runs in two modes, set with `GLOSA_MODE`:

- `selfhost` (default): one reader on their own computer, no sign-in, extras installed through Docker.
- `hosted`: a web service. Accounts by invitation, sign-in required, every reader's books, vocabulary, settings and keys kept apart, Docker extras disabled. Create the first admin on the server with `docker compose exec api python -m app.cli create-admin you@example.com`, then invite people from **Ajustes → Invitaciones**. Set `GLOSA_PUBLIC_URL` to the address invitation links should use.

The database schema is versioned with Alembic (`api/migrations`) and upgraded when the API starts; a database from 0.1.0 is recognised and upgraded with its data.

## Running it for development

Everything runs in containers; you only need Docker.

```sh
docker compose up -d          # web on http://localhost:5174, API on http://localhost:8001
docker compose run --rm api pytest
```

A release (`git tag v0.1.0 && git push --tags`) runs `.github/workflows/release.yml`: it publishes the images to ghcr.io and attaches the Windows installer to the GitHub release.

AI features read their API keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`) from the environment, injected by [Doppler](https://www.doppler.com/) at start-up:

```sh
doppler run --project shared --config dev -- docker compose up -d
```

Keys can also be pasted under **Ajustes → Modelo de IA**; they are stored encrypted (Fernet) with a master key from `GLOSA_SECRET_KEY`, or one generated in the `api-data` volume. A key from the environment takes priority. Without any key, AI buttons report it and everything else (dictionary, local translator) keeps working. Pick the provider and model in the same place: Anthropic, OpenAI, DeepSeek, or any OpenAI-compatible server such as Ollama.

Pronunciation uses Wiktionary's recordings for single words and a local speech engine for everything else: Kokoro-82M or Supertonic 3 (extras), compared under **Ajustes → Voz**. The browser's own voice is the last fallback.

Phrases and sentences are translated by default by a translation model in [Ollama](https://ollama.com): the host's when it runs one, otherwise the one the app installs as an extra. It runs on the CPU unless the graphics card is enabled in **Ajustes → Traducción**, and reads the sentence around the selected fragment, so it picks the sense the fragment has there ("In relating" → "Al relatar"). Without it, the basic translator (LibreTranslate) translates instead; the paid AI can also be chosen. Every translation is cached in the database.

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
