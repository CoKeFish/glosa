import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router";
import { api, BookSummary, DrillPrompt, DrillRound, Topic } from "../api";
import { useI18n } from "../i18n";

const MARK: Record<Topic["status"], string> = { no_visto: "⬜", falla: "🟡", dominado: "🟢" };
const NEXT: Record<Topic["status"], Topic["status"]> = { no_visto: "falla", falla: "dominado", dominado: "no_visto" };

/** Guided practice: translation rounds, their history, the syllabus and the mistakes made. */
export function Drills() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [status, setStatus] = useState<Awaited<ReturnType<typeof api.drillsStatus>> | null>(null);
  const [rounds, setRounds] = useState<DrillRound[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [errors, setErrors] = useState<{ tag: string; count: number }[]>([]);
  const [books, setBooks] = useState<BookSummary[]>([]);
  const [bookId, setBookId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = () => {
    api.drillsStatus().then(setStatus).catch((e) => setError(e.message));
    api.rounds().then(setRounds).catch(() => {});
    api.syllabus().then(setTopics).catch(() => {});
    api.drillStats().then((s) => setErrors(s.errors)).catch(() => {});
  };
  useEffect(() => {
    load();
    api.books().then((b) => setBooks(b.filter((x) => x.language === "en"))).catch(() => {});
  }, []);

  async function start() {
    setBusy(true);
    setError("");
    try {
      const round = await api.newRound(bookId);
      navigate(`/drills/${round.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  const blocks = useMemo(() => {
    const map = new Map<string, Topic[]>();
    topics.forEach((topic) => map.set(topic.block, [...(map.get(topic.block) ?? []), topic]));
    return [...map.entries()];
  }, [topics]);
  const counts = useMemo(
    () => ({ dominado: topics.filter((x) => x.status === "dominado").length, falla: topics.filter((x) => x.status === "falla").length,
             no_visto: topics.filter((x) => x.status === "no_visto").length }),
    [topics],
  );

  async function cycle(topic: Topic) {
    const updated = await api.patchTopic(topic.id, { status: NEXT[topic.status] });
    setTopics((all) => all.map((x) => (x.id === topic.id ? updated : x)));
  }
  async function activate(topic: Topic) {
    await api.patchTopic(topic.id, { active: true });
    setTopics((all) => all.map((x) => ({ ...x, active: x.id === topic.id })));
  }
  async function importFile(file: File) {
    setError("");
    try {
      await api.importSyllabus(file);
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const ready = status?.ready ?? false;
  const maxErrors = Math.max(1, ...errors.map((e) => e.count));

  return (
    <div className="page narrow drills">
      <header className="page-head">
        <h1>{t("dr.title")}</h1>
        <p className="muted">{t("dr.intro")}</p>
      </header>

      {status && !ready && (
        <section className="card notice" role="status">
          <h2>{t("dr.needsAi")}</h2>
          <p className="muted" style={{ margin: 0 }}>{t("dr.needsAiHelp")}</p>
          {status.reason && <p className="small warn" style={{ margin: 0 }}>{status.reason}</p>}
          <Link className="btn" to="/settings">{t("dr.goSettings")}</Link>
        </section>
      )}
      {error && <p className="error">{error}</p>}

      <section className="card">
        <h2>{t("dr.newRound")}</h2>
        <p className="muted small" style={{ margin: 0 }}>{t("dr.newRoundHelp")}</p>
        <div className="key-row" style={{ flexWrap: "wrap" }}>
          <select value={bookId ?? ""} onChange={(e) => setBookId(e.target.value ? Number(e.target.value) : null)}
                  aria-label={t("dr.fromBook")}>
            <option value="">{t("dr.noBook")}</option>
            {books.map((b) => <option key={b.id} value={b.id}>{t("dr.vocabFrom", { title: b.title })}</option>)}
          </select>
          <button disabled={!ready || busy} onClick={start}>{busy ? t("dr.writing") : t("dr.start")}</button>
        </div>
      </section>

      <section className="card">
        <h2>{t("dr.history")}</h2>
        {rounds.length === 0 ? (
          <p className="muted small" style={{ margin: 0 }}>{t("dr.noRounds")}</p>
        ) : (
          <ul className="extras-list">
            {rounds.map((r) => (
              <li key={r.id} className="extra">
                <Link to={`/drills/${r.id}`} className="extra-text round-link">
                  <strong>{t("dr.round", { n: String(r.id) })}</strong>
                  <span className="muted small">{r.created_at ? new Date(r.created_at).toLocaleString() : ""}</span>
                </Link>
                {r.corrected_at ? (
                  <span className={`pill ${r.correct === r.total ? "ok" : ""}`}>{t("dr.score", { n: String(r.correct), total: String(r.total) })}</span>
                ) : (
                  <span className="pill">{t("dr.pending")}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2>{t("dr.errors")}</h2>
        {errors.length === 0 ? (
          <p className="muted small" style={{ margin: 0 }}>{t("dr.noErrors")}</p>
        ) : (
          <ul className="bars" aria-label={t("dr.errors")}>
            {errors.slice(0, 12).map((e) => (
              <li key={e.tag}>
                <span className="bar-label">{e.tag.replace(/_/g, " ")}</span>
                <span className="bar-track"><span className="bar" style={{ width: `${(100 * e.count) / maxErrors}%` }} /></span>
                <span className="bar-n">{e.count}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <div className="card-head">
          <h2>{t("dr.syllabus")}</h2>
          <span className="muted small">🟢 {counts.dominado} · 🟡 {counts.falla} · ⬜ {counts.no_visto}</span>
        </div>
        <p className="muted small" style={{ margin: 0 }}>{t("dr.syllabusHelp")}</p>
        <div className="syllabus">
          {blocks.map(([block, items]) => (
            <div key={block} className="syllabus-block">
              <h3>{block}</h3>
              <ul>
                {items.map((topic) => (
                  <li key={topic.id} className={topic.active ? "active" : ""}>
                    <button className="marker" onClick={() => cycle(topic)} title={t(`dr.status.${topic.status}` as "dr.status.falla")}
                            aria-label={`${t(`dr.status.${topic.status}` as "dr.status.falla")}: ${topic.description}`}>
                      {MARK[topic.status]}
                    </button>
                    <span className="topic-text">{topic.description}</span>
                    {topic.active ? (
                      <span className="pill ok">{t("dr.active")}</span>
                    ) : (
                      <button className="btn-ghost small" onClick={() => activate(topic)}>{t("dr.makeActive")}</button>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <label className="btn-ghost file-pick">
          {t("dr.import")}
          <input type="file" accept=".md,text/markdown,text/plain" hidden
                 onChange={(e) => e.target.files?.[0] && importFile(e.target.files[0])} />
        </label>
      </section>

      <section className="card">
        <h2>{t("dr.anki")}</h2>
        <p className="muted small" style={{ margin: 0 }}>{t("dr.ankiHelp")}</p>
        <div className="key-row" style={{ flexWrap: "wrap" }}>
          <a className="btn" href="/api/terms/export.apkg?language=en&tag=drills">{t("dr.ankiApkg")}</a>
          <a className="btn-ghost" href="/api/terms/export.csv?language=en&tag=drills">{t("dr.ankiCsv")}</a>
        </div>
      </section>

      <PromptsCard />
    </div>
  );
}

function PromptsCard() {
  const { t } = useI18n();
  const [prompts, setPrompts] = useState<Record<string, DrillPrompt> | null>(null);
  const [open, setOpen] = useState<"generator" | "corrector" | null>(null);
  const [draft, setDraft] = useState("");
  const [message, setMessage] = useState("");

  const load = () => api.drillPrompts().then(setPrompts).catch(() => {});
  useEffect(() => {
    load();
  }, []);

  async function save(name: "generator" | "corrector", text: string) {
    setMessage("");
    try {
      await api.putDrillPrompt(name, text);
      setMessage(text ? t("dr.promptSaved") : t("dr.promptReset"));
      load();
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  if (!prompts) return null;
  return (
    <section className="card">
      <h2>{t("dr.prompts")}</h2>
      <p className="muted small" style={{ margin: 0 }}>{t("dr.promptsHelp")}</p>
      {(["generator", "corrector"] as const).map((name) => (
        <div key={name} className="prompt-row">
          <div className="extra">
            <div className="extra-text">
              <strong>{t(`dr.prompt.${name}` as "dr.prompt.corrector")}</strong>
              <span className="muted small">
                {prompts[name].custom ? t("dr.promptCustom") : t("dr.promptFile", { file: prompts[name].file })}
              </span>
            </div>
            <button className="btn-ghost" onClick={() => { setOpen(open === name ? null : name); setDraft(prompts[name].text); setMessage(""); }}>
              {open === name ? t("dr.close") : t("dr.edit")}
            </button>
          </div>
          {open === name && (
            <>
              <textarea className="prompt-editor" value={draft} onChange={(e) => setDraft(e.target.value)} spellCheck={false} />
              <div className="key-row">
                <button onClick={() => save(name, draft)}>{t("dr.save")}</button>
                {prompts[name].custom && <button className="btn-ghost" onClick={() => save(name, "")}>{t("dr.useFile")}</button>}
              </div>
            </>
          )}
        </div>
      ))}
      {message && <p className="muted small" style={{ margin: 0 }}>{message}</p>}
    </section>
  );
}
