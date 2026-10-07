import { FormEvent, Fragment, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { api, DrillRound as Round, Topic } from "../api";
import { diffWords, Piece } from "../drillDiff";
import { useI18n } from "../i18n";
import { Speaker } from "../icons";
import { speak } from "../speech";

function Pieces({ pieces, kind }: { pieces: Piece[]; kind: "del" | "add" }) {
  return (
    <>
      {pieces.map((p, i) => (
        <Fragment key={i}>
          {i > 0 && " "}
          {p.changed ? (kind === "del" ? <del>{p.text}</del> : <mark>{p.text}</mark>) : p.text}
        </Fragment>
      ))}
    </>
  );
}

function Listen({ text, label }: { text: string; label: string }) {
  return (
    <button type="button" className="icon-btn listen" onClick={() => speak(text, "en")} title={label} aria-label={`${label}: ${text}`}>
      <Speaker size={16} />
    </button>
  );
}

/** One round: the 7 sentences to translate, then the correction. */
export function DrillRound() {
  const { t } = useI18n();
  const { roundId } = useParams();
  const navigate = useNavigate();
  const [round, setRound] = useState<Round | null>(null);
  const [topics, setTopics] = useState<Record<number, Topic>>({});
  const [answers, setAnswers] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.round(Number(roundId)).then((r) => {
      setRound(r);
      setAnswers((r.items ?? []).map((i) => i.answer));
    }).catch((e) => setError(e.message));
    api.syllabus().then((all) => setTopics(Object.fromEntries(all.map((x) => [x.id, x])))).catch(() => {});
  }, [roundId]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!round) return;
    setBusy(true);
    setError("");
    try {
      setRound(await api.submitRound(round.id, answers));
      window.scrollTo({ top: 0 });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!round) return;
    await api.deleteRound(round.id);
    navigate("/drills");
  }

  if (!round) return <div className="page narrow muted">{error || t("loading")}</div>;
  const items = round.items ?? [];
  const corrected = round.corrected_at !== null;
  const topicNames = (ids: number[]) => ids.map((id) => topics[id]?.description).filter(Boolean).join(" · ");

  return (
    <div className="page drills-round">
      <header className="page-head">
        <Link to="/drills" className="muted small">← {t("dr.title")}</Link>
        <h1>{t("dr.round", { n: String(round.id) })}</h1>
        {corrected && <p className="lead-score">{t("dr.score", { n: String(round.correct), total: String(round.total) })}</p>}
      </header>
      {error && <p className="error" role="alert">{error}</p>}

      {!corrected ? (
        <form className="card drill-form" onSubmit={submit}>
          <p className="muted small" style={{ margin: 0 }}>{t("dr.translateHelp")}</p>
          <ol className="drill-items">
            {items.map((item, i) => (
              <li key={item.id}>
                <label htmlFor={`a${i}`} className="drill-spanish">{item.spanish}</label>
                <span className="muted small topic-hint">{topicNames(item.topic_ids)}</span>
                <textarea id={`a${i}`} rows={2} lang="en" spellCheck={false} value={answers[i] ?? ""}
                          onChange={(e) => setAnswers((all) => all.map((v, j) => (j === i ? e.target.value : v)))} />
              </li>
            ))}
          </ol>
          <div className="key-row">
            <button disabled={busy || answers.every((a) => !a.trim())}>{busy ? t("dr.correcting") : t("dr.correct")}</button>
            <button type="button" className="btn-ghost" onClick={remove}>{t("dr.discard")}</button>
          </div>
        </form>
      ) : (
        <>
          <section className="card">
            <div className="table-scroll">
              <table className="drill-table">
                <thead>
                  <tr><th>#</th><th>{t("dr.colSpanish")}</th><th>{t("dr.colYours")}</th><th>{t("dr.colFix")}</th></tr>
                </thead>
                <tbody>
                  {items.map((item, i) => {
                    const d = diffWords(item.answer, item.correction);
                    return (
                      <tr key={item.id} className={item.verdict === "correcta" ? "ok" : "bad"}>
                        <td className="num">{i + 1}</td>
                        <td>{item.spanish}</td>
                        <td lang="en">{item.answer ? <Pieces pieces={d.answer} kind="del" /> : <span className="muted">—</span>}</td>
                        <td lang="en">
                          <span className="fix-line">
                            <span>{item.verdict === "correcta" ? item.correction : <Pieces pieces={d.correction} kind="add" />}</span>
                            <Listen text={item.correction} label={t("dr.listen")} />
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <section className="card">
            <h2>{t("dr.explanations")}</h2>
            <ol className="explanations">
              {items.map((item) => (
                <li key={item.id} className={item.verdict === "correcta" ? "ok" : "bad"}>
                  <p className="explanation">{item.explanation}</p>
                  {item.examples.length > 0 && (
                    <ul className="examples">
                      {item.examples.map((ex) => (
                        <li key={ex} lang="en"><Listen text={ex} label={t("dr.listen")} /> {ex}</li>
                      ))}
                    </ul>
                  )}
                  {(item.error_tags.length > 0 || item.failed_topic_ids.length > 0) && (
                    <div className="tags">
                      {item.error_tags.map((tag) => <span key={tag} className="pill">{tag.replace(/_/g, " ")}</span>)}
                      {item.failed_topic_ids.length > 0 && <span className="muted small">{t("dr.failedTopic", { topics: topicNames(item.failed_topic_ids) })}</span>}
                    </div>
                  )}
                </li>
              ))}
            </ol>
          </section>

          {round.closing_note && (
            <section className="card">
              <h2>{t("dr.closing")}</h2>
              <p style={{ margin: 0 }}>{round.closing_note}</p>
              <p className="muted small" style={{ margin: 0 }}>{t("dr.toReview")}</p>
              <div className="key-row">
                <Link className="btn" to="/review">{t("dr.goReview")}</Link>
                <Link className="btn-ghost" to="/drills">{t("dr.backToDrills")}</Link>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
