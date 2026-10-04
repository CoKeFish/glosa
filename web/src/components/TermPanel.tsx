import { useEffect, useRef, useState } from "react";
import { api, DictionaryResult, IGNORED, KNOWN, Section, Term } from "../api";
import { useI18n } from "../i18n";
import { Ban, Check, Close, External, Speaker, Sparkle } from "../icons";
import { play, speak } from "../speech";
import { MAX_SAVED_PHRASE_WORDS, Selection, selectionText, sentenceText } from "../reading";

type Props = {
  section: Section;
  selection: Selection;
  term: Term | undefined;
  onSaved: (term: Term) => void;
  onSelect: (s: Selection) => void;
  onClose: () => void;
  activeGrammar: number | null;
  onGrammar: (index: number | null) => void;
  /** Save a new term as status 1 as soon as it opens: clicking it means the reader doesn't know it. */
  autoSave: boolean;
};

const MAX_SUGGESTIONS = 6;

/** One line telling what the current status means in practice. */
function statusHint(term: Term | undefined, t: ReturnType<typeof useI18n>["t"]): string {
  if (!term) return t("card.hint.none");
  if (term.status === KNOWN) return t("card.hint.known");
  if (term.status === IGNORED) return t("card.hint.ignored");
  return t(`card.hint.${term.status}` as "card.hint.1");
}
const PROVIDERS = ["local", "ai"] as const;
type Provider = (typeof PROVIDERS)[number];
/** text is null when the translator could not translate it (message says why). */
type Translations = Partial<Record<Provider, { text: string | null; message?: string }>>;

export function TermPanel({ section, selection, term, onSaved, onSelect, onClose, activeGrammar, onGrammar, autoSave }: Props) {
  const { t } = useI18n();
  const language = section.book.language;
  const sentenceIndex = section.tokens[selection.tokens[0]].s;
  const context = sentenceText(section.tokens, sentenceIndex);
  const surface = selectionText(section.tokens, selection.tokens);
  const title = selection.kind === "word" ? surface : selection.key;

  const [meaning, setMeaning] = useState(term?.meaning ?? "");
  // Auto-save in two steps: the term turns yellow right away, and gets the best meaning
  // once the dictionary answers. Refs keep each step from running twice.
  const autoSaving = useRef(autoSave && !term);
  const autoMeaning = useRef(autoSave && !term?.meaning);
  const [dict, setDict] = useState<DictionaryResult | null>(null);
  const [ai, setAi] = useState<{ explanation: string; is_phrasal_verb: boolean } | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [grammarAi, setGrammarAi] = useState("");
  const [grammarBusy, setGrammarBusy] = useState(false);
  // Translations by provider, so the local and the AI version can be compared side by side.
  const [sentenceTranslations, setSentenceTranslations] = useState<Translations>({});
  const [phraseTranslations, setPhraseTranslations] = useState<Translations>({});
  const [translating, setTranslating] = useState<string | null>(null);
  const [found, setFound] = useState<{ text: string; base: string; meaning: string }[] | null>(null);
  const [findingBusy, setFindingBusy] = useState(false);
  const [savedFound, setSavedFound] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");
  const meaningRef = useRef<HTMLInputElement>(null);

  // Phrases and expressions get a sentence-style translation too: the dictionary often has
  // no entry in the reader's language for them ("at any rate").
  const isPhrase = selection.kind === "phrase" || selection.kind === "expression";
  const phraseText = surface.replace(/ … /g, " ");
  const tooLong = isPhrase && selection.key.split(" ").length > MAX_SAVED_PHRASE_WORDS;

  useEffect(() => {
    let cancelled = false;
    // Long selections are translated, not looked up: no dictionary has whole sentences.
    if (!tooLong) {
      api
        .dictionary({
          language,
          term: selection.key,
          lemma: selection.lemma,
          surface: selection.kind === "word" ? surface : selection.key,
          context,
          kind: selection.kind,
        })
        .then((d) => {
          if (cancelled) return;
          setDict(d);
          if (d.sentence_translation) setSentenceTranslations((p) => ({ local: { text: d.sentence_translation }, ...p }));
        })
        .catch((e) => !cancelled && setError(e.message));
    }
    if (isPhrase) {
      api
        .translateText(language, phraseText)
        .then((r) => !cancelled && setPhraseTranslations({ [r.provider]: { text: r.translation, message: r.message } }))
        .catch((e) => !cancelled && setError(e.message));
    }
    return () => {
      cancelled = true;
    };
  }, [language, selection.key, selection.lemma, selection.kind, surface, context, isPhrase, tooLong, phraseText]);

  async function translateWith(target: "phrase" | "sentence", provider: Provider) {
    setTranslating(`${target}:${provider}`);
    setError("");
    try {
      const r = await api.translateText(language, target === "phrase" ? phraseText : context, provider);
      (target === "phrase" ? setPhraseTranslations : setSentenceTranslations)((p) => ({
        ...p,
        [r.provider]: { text: r.translation, message: r.message },
      }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setTranslating(null);
    }
  }

  async function save(status?: number, meaningOverride?: string) {
    setError("");
    try {
      const saved = await api.saveTerm({
        language,
        key: selection.key,
        kind: selection.kind,
        status,
        meaning: meaningOverride ?? meaning,
        context: term?.context || context,
      });
      onSaved(saved);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function choose(text: string) {
    // Like LingQ: picking a meaning saves the term.
    autoMeaning.current = false;
    setMeaning(text);
    save(undefined, text);
  }

  useEffect(() => {
    if (!autoSaving.current || tooLong) return;
    autoSaving.current = false;
    save(1, "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!autoMeaning.current || !dict || tooLong) return;
    autoMeaning.current = false;
    const best = dict.translations.find((s) => s.fits) ?? dict.translations[0];
    if (best) {
      setMeaning(best.text);
      save(undefined, best.text);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dict]);

  async function explain() {
    setAiBusy(true);
    setError("");
    try {
      const r = await api.explain({ language, term: surface, kind: selection.kind, context });
      setAi(r);
      if (!meaning) setMeaning(r.translation);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAiBusy(false);
    }
  }

  function TranslationList({ target, items }: { target: "phrase" | "sentence"; items: Translations }) {
    const missing = PROVIDERS.filter((p) => !items[p]);
    return (
      <>
        {PROVIDERS.filter((p) => items[p]).map((p) => {
          const item = items[p]!;
          return (
            <div key={p} className="translation-item">
              <span className="translation-source">{p === "local" ? t("card.byLocal") : t("card.byAi")}</span>
              {item.text ? (
                <p className="translation-text">{item.text}</p>
              ) : (
                <p className="translation-text muted">{p === "local" ? t("card.localFailed") : item.message}</p>
              )}
              {item.text && target === "phrase" && !tooLong && meaning !== item.text && (
                <button className="btn-ghost" onClick={() => choose(item.text!)}>{t("card.useTranslation")}</button>
              )}
            </div>
          );
        })}
        <div className="translate-actions">
          {missing.map((p) => (
            <button key={p} className="ai-btn" disabled={translating !== null} onClick={() => translateWith(target, p)}>
              {p === "ai" && <Sparkle />}
              {translating === `${target}:${p}`
                ? t("card.translating")
                : t(p === "ai" ? "card.translateAi" : "card.translateLocal")}
            </button>
          ))}
        </div>
      </>
    );
  }

  const grammarHere = section.grammar.map((g, index) => ({ ...g, index })).filter((g) => g.s === sentenceIndex);

  async function findExpressions() {
    setFindingBusy(true);
    setError("");
    try {
      // Tell the AI what the automatic detection already marked in this sentence.
      const known = section.units
        .filter((u) => u.kind !== "phrase" && section.tokens[u.i[0]].s === sentenceIndex)
        .map((u) => u.k);
      setFound((await api.findExpressions(language, context, known)).expressions);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setFindingBusy(false);
    }
  }

  async function saveFound(e: { base: string; meaning: string }) {
    try {
      const saved = await api.saveTerm({ language, key: e.base, kind: "expression", status: 1, meaning: e.meaning, context });
      setSavedFound((s) => new Set(s).add(e.base));
      onSaved(saved);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function explainGrammar() {
    setGrammarBusy(true);
    try {
      const structures = grammarHere.map((g) => `${g.label}: "${selectionText(section.tokens, g.i)}"`);
      setGrammarAi((await api.explainGrammar(language, context, structures)).explanation);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setGrammarBusy(false);
    }
  }

  // Status shortcuts while the card is open.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(tag) || e.ctrlKey || e.metaKey) return;
      const statuses: Record<string, number> = { "1": 1, "2": 2, "3": 3, "4": 4, k: KNOWN, x: IGNORED };
      if (e.key in statuses) {
        e.preventDefault();
        save(statuses[e.key]);
      } else if (e.key === "h") {
        e.preventDefault();
        meaningRef.current?.focus();
      } else if (e.key === "s") {
        e.preventDefault();
        sayTerm();
      } else if (e.key === "a") {
        e.preventDefault();
        saySentence();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const kindLabel =
    selection.kind === "phrasal_verb"
      ? t(selection.sub === "prepositional" ? "card.kind.prepositional" : "card.kind.phrasal")
      : selection.kind === "expression"
        ? t("card.kind.expression")
        : tooLong
        ? t("card.kind.sentence")
        : selection.kind === "phrase"
          ? t("card.kind.phrase")
          : t("card.kind.word");
  const kindClass =
    selection.kind === "phrasal_verb"
      ? "tag phrasal"
      : selection.kind === "expression"
        ? "tag expression"
        : selection.kind === "phrase"
          ? "tag phrase"
          : "tag";
  const suggestions = dict?.translations.slice(0, MAX_SUGGESTIONS) ?? [];
  // The local translator gave up and nothing else translated it: if the dictionary has
  // suggestions, the failure notice is just noise.
  const onlyFailedTranslation =
    !!phraseTranslations.local && !phraseTranslations.local.text && !phraseTranslations.ai;
  const statusTitle = (s: number) => t(`card.status.${s}` as "card.status.1");

  const spoken = isPhrase || selection.kind === "phrasal_verb" ? phraseText : surface;
  const recording = dict?.pronunciation?.audio[0]?.url;
  const ipa = dict?.pronunciation?.ipa[0];
  const sayTerm = () => play(selection.kind === "word" ? recording : undefined, spoken, language);
  const saySentence = () => speak(context, language);

  return (
    <div className="word-card">
      <div className="word-card-head">
        <button className="icon-btn speak-btn" aria-label={t("card.listen")} title={`${t("card.listen")} (S)`} onClick={sayTerm}>
          <Speaker />
        </button>
        <h2>
          {title}
          {ipa && selection.kind === "word" && <span className="ipa">{ipa}</span>}
        </h2>
        {tooLong || !term ? null : term.status === KNOWN ? (
          <span className="status-pill known"><Check size={13} /> {t("card.iKnowIt")}</span>
        ) : term.status === IGNORED ? (
          <span className="status-pill ignored">{t("card.ignored")}</span>
        ) : (
          <span className="status-pill">{statusTitle(term.status)}</span>
        )}
        <button className="icon-btn" aria-label={t("card.close")} onClick={onClose}><Close size={18} /></button>
      </div>
      <div className="tags">
        <span className={kindClass}>{kindLabel}</span>
        {(selection.kind === "phrasal_verb" || selection.kind === "expression") &&
          surface.toLowerCase() !== selection.key && <span className="tag">«{surface}»</span>}
        {selection.lemma && selection.lemma !== selection.key && (
          <span className="tag">{t("card.baseForm", { lemma: selection.lemma })}</span>
        )}
      </div>

      <div className="word-card-body">
        {selection.word && (
          <p className="muted small" style={{ margin: 0 }}>
            {t("card.clickAgain")}{" "}
            <button className="btn-ghost alt-link" onClick={() => onSelect(selection.word!)}>
              {t("card.onlyWord", { word: section.tokens[selection.word.tokens[0]].t })}
            </button>
          </p>
        )}
        {ai && selection.kind === "phrasal_verb" && !ai.is_phrasal_verb && (
          <p className="warn small" style={{ margin: 0 }}>{t("card.literal")}</p>
        )}

        {isPhrase && !(onlyFailedTranslation && suggestions.length > 0) && (
          <div className="translation-box">
            <p className="field-label">{t("card.translation")}</p>
            {Object.keys(phraseTranslations).length === 0 && translating === null && (
              <p className="translation-text muted">{t("card.translating")}</p>
            )}
            <TranslationList target="phrase" items={phraseTranslations} />
          </div>
        )}

        {!tooLong && <>
        {/* The meaning field only exists once the term is in the vocabulary: before that,
            picking a suggestion or a translation is how it gets saved. */}
        {term && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              save();
            }}
            style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}
          >
            <p className="field-label">
              {t("card.savedMeaning")} <span className="muted small" style={{ fontWeight: 400 }}>{t("card.meaningHelp")}</span>
            </p>
            <input
              ref={meaningRef}
              className="meaning-input"
              placeholder={t("card.meaningPlaceholder")}
              value={meaning}
              onChange={(e) => setMeaning(e.target.value)}
              onBlur={() => meaning !== term.meaning && save()}
            />
          </form>
        )}

        {!(isPhrase && suggestions.length === 0) && (
          <div className="suggestions">
            <p className="field-label">{t("card.suggestions")}</p>
            {!dict && <p className="muted small">{t("card.searching")}</p>}
            {dict && suggestions.length === 0 && <p className="muted small" style={{ margin: 0 }}>{t("card.noSuggestions")}</p>}
            <div className="suggestion-grid">
              {suggestions.map((s) => (
                <button
                  key={s.text}
                  className={`suggestion ${s.fits ? "fits" : ""} ${meaning === s.text ? "chosen" : ""}`}
                  onClick={() => choose(s.text)}
                  title={`${s.sense}${s.sense ? " — " : ""}${t("card.useAsMeaning")}`}
                >
                  <span className="suggestion-text">
                    {s.text}
                    {s.fits && <span className="fit-badge">{t("card.bestFit")}</span>}
                  </span>
                  {s.sense && <span className="suggestion-sense">{s.sense}</span>}
                </button>
              ))}
            </div>
          </div>
        )}

        {!(selection.kind === "phrase" && !term) && (
        <div className="status-block">
          <p className="field-label">{t("card.howWell")}</p>
          <div className="level-bar" role="group" aria-label={t("card.howWell")}>
            {[1, 2, 3, 4].map((s) => {
              const level = term && term.status >= 1 && term.status <= 4 ? term.status : 0;
              return (
                <button
                  key={s}
                  className={`level ${s <= level ? "filled" : ""} ${s === level ? "on" : ""}`}
                  title={t(`card.statusHelp.${s}` as "card.statusHelp.1")}
                  onClick={() => save(s)}
                >
                  {statusTitle(s)}
                </button>
              );
            })}
          </div>
          <div className="status-actions">
            <button className={`known ${term?.status === KNOWN ? "on" : ""}`} onClick={() => save(KNOWN)}>
              <Check /> {t("card.iKnowIt")}
            </button>
            <button className={`ignored ${term?.status === IGNORED ? "on" : ""}`} onClick={() => save(IGNORED)}>
              <Ban /> {t("card.ignore")}
            </button>
          </div>
          <p className="status-hint">{statusHint(term, t)}</p>
        </div>
        )}

        <button className="ai-btn" onClick={explain} disabled={aiBusy}>
          <Sparkle /> {aiBusy ? t("card.asking") : t("card.explainAi")}
        </button>
        </>}
        {ai && <div className="ai-box">{ai.explanation}</div>}
        {error && <p className="error small" style={{ margin: 0 }}>{error}</p>}
      </div>

      <div className="panel-section">
        <h3 className="with-action">
          {t("card.sentence")}
          <button className="icon-btn" aria-label={t("card.listenSentence")} title={`${t("card.listenSentence")} (A)`} onClick={saySentence}>
            <Speaker size={18} />
          </button>
        </h3>
        <p className="sentence">{context}</p>
        <div className="translation-box">
          <TranslationList target="sentence" items={sentenceTranslations} />
        </div>
        <div className="found-expressions">
          {found === null ? (
            <button className="ai-btn" disabled={findingBusy} onClick={findExpressions}>
              <Sparkle /> {findingBusy ? t("card.asking") : t("card.findExpressions")}
            </button>
          ) : found.length === 0 ? (
            <p className="muted small" style={{ margin: 0 }}>{t("card.noExpressionsFound")}</p>
          ) : (
            <>
              <p className="field-label">{t("card.expressionsFound")}</p>
              {found.map((e) => (
                <div key={e.base} className="found-item">
                  <div>
                    <strong>{e.base}</strong>
                    {e.text.toLowerCase() !== e.base && <span className="muted small"> · «{e.text}»</span>}
                    <div className="small">{e.meaning}</div>
                  </div>
                  {savedFound.has(e.base) ? (
                    <span className="ok small">{t("card.saved")}</span>
                  ) : (
                    <button className="btn-ghost" onClick={() => saveFound(e)}>{t("card.save")}</button>
                  )}
                </div>
              ))}
              <p className="muted small" style={{ margin: 0 }}>{t("card.expressionsFoundHelp")}</p>
            </>
          )}
        </div>
      </div>

      {grammarHere.length > 0 && (
        <div className="panel-section">
          <h3>{t("card.grammar")}</h3>
          <ul className="grammar-list">
            {grammarHere.map((g) => {
              const lemma = g.lemma;
              return (
                <li key={g.index}>
                  <button
                    className={`grammar-item ${activeGrammar === g.index ? "on" : ""}`}
                    onClick={() => onGrammar(activeGrammar === g.index ? null : g.index)}
                  >
                    <span className="grammar-head">
                      <strong>{g.label}</strong>
                      <span className="grammar-fragment">
                        «{selectionText(section.tokens, g.i)}»
                        {lemma && <> · {t("card.grammarFrom", { lemma })}</>}
                      </span>
                    </span>
                    <span className="grammar-explain">{g.explanation}</span>
                  </button>
                </li>
              );
            })}
          </ul>
          {grammarAi ? (
            <div className="ai-box" style={{ marginTop: "0.6rem", whiteSpace: "pre-wrap" }}>{grammarAi}</div>
          ) : (
            <button className="ai-btn" style={{ marginTop: "0.6rem" }} onClick={explainGrammar} disabled={grammarBusy}>
              <Sparkle /> {grammarBusy ? t("card.asking") : t("card.grammarAi")}
            </button>
          )}
        </div>
      )}

      <div className="panel-section">
        <h3>{t("card.dictionary")}</h3>
        {!dict && <p className="muted small">{t("card.searching")}</p>}
        {dict && dict.results.length === 0 && <p className="muted small">{t("card.noEntries")}</p>}
        {dict?.results.map((r) => (
          <div key={r.term + r.source}>
            <p className="dict-source">{r.term}</p>
            {r.entries.map((entry, n) => (
              <div key={n}>
                <p className="dict-pos">{entry.part_of_speech}</p>
                <ol className="dict-defs">
                  {entry.definitions.map((d, m) => <li key={m}>{d}</li>)}
                </ol>
              </div>
            ))}
          </div>
        ))}
        {dict && dict.links.length > 0 && (
          <div className="dict-links">
            {dict.links.map((l) => (
              <a key={l.name} href={l.url} target="_blank" rel="noreferrer">{l.name} <External /></a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
