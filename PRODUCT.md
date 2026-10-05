# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Readers learning a foreign language through texts they choose themselves (books, articles), in any language pair. Today the reader studies English with meanings and explanations in Spanish, French, Portuguese or Italian; the interface is in Spanish or English. They read for long stretches on a desktop or laptop, look words up mid-sentence and come back to their saved vocabulary in reviews.

## Product Purpose

glosa is an open source reader for learning languages by reading, in the tradition of LingQ, without its courses. You import your own texts, read them with every word marked by how well you know it, look up words and expressions in context, and review what you saved. Success: a reader finishes real books in the language they are learning, and their known-word count grows as they do.

## Positioning

What glosa defends, chosen by the user (2026-10-05):

- **Local and private.** It runs on the reader's own computer (Docker). Translation and speech can run locally (a translation model in Ollama, Kokoro voices), so texts need not leave the machine. Cloud AI is optional.
- **Free and open source.** No subscription; AGPL-3.0; vocabulary exportable (CSV).
- **Your own texts.** You read what you choose (EPUB, TXT, HTML, pasted text), not lessons from a catalogue.

Context-aware help (meanings ranked for the sentence, expressions and phrasal verbs detected, grammar explained) is a real capability, but the user did not pick it as the brand's lead claim.

## Operating Context

Self-hosted: `docker compose up -d`, then the app at localhost:5174. Optional Ollama on the host for local translation. Secrets live in Doppler. The landing page is a static page at https://glosa.suchima.com, served from `landing/` on the user's VPS.

## Capabilities and Constraints

- Import EPUB, TXT, HTML or pasted text; reader with word statuses (new, recognized, familiar, learned, known, ignored), layered clicks (expression first, then the word), page-turn marks words known.
- Dictionary: Wiktionary via Kaikki (English edition plus the edition in the reader's language), meanings ranked for the sentence, pronunciation recordings.
- Detection: ~13,000 expressions, phrasal verbs (inflected and separated), grammar structures with explanations.
- Translation of phrases: local model (TranslateGemma via Ollama, CPU by default), LibreTranslate, or cloud AI (Anthropic, OpenAI, DeepSeek, OpenAI-compatible); cached.
- Speech: Wiktionary recordings, Kokoro and Supertonic local voices, browser voice.
- Spaced review; AI cost tracking.
- Studied language today: English only. More languages are planned as packs, not yet built.
- Early development: no hosted version, no accounts, no mobile app.

## Brand Commitments

- Name: **glosa** (lowercase). "Glosa" is Spanish for a gloss, the note that explains a word in a text. The user kept only the name; icon, colours, type and landing are open to redesign (2026-10-05).
- Repository: https://github.com/CoKeFish/glosa. License AGPL-3.0.
- Interface copy exists in Spanish and English.

## Evidence on Hand

- The working app (screenshots can be taken from localhost:5174) and real reading examples from H. P. Lovecraft's "The Tomb" (public domain), already used to compare with LingQ.
- No users, testimonials, download numbers, press or benchmarks. None may be invented.

## Product Principles

1. The reader's text comes first; tools appear around it, never over it.
2. Nothing leaves the reader's computer unless they choose a cloud service, and then they see what it costs.
3. Free means free: no paywall, no account, no lock-in.
4. Honest about scope: say what works today and what is planned.
