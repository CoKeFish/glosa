import { useEffect, useState } from "react";
import { api, IGNORED, KNOWN, Term } from "../api";
import { useI18n } from "../i18n";
import { Ban, Check } from "../icons";
import { useStudyLanguage } from "../Layout";

function StatusMini({ status }: { status: number }) {
  if (status === KNOWN) return <span className="status-mini known"><Check size={14} /></span>;
  if (status === IGNORED) return <span className="status-mini ignored"><Ban size={14} /></span>;
  return <span className="status-mini">{status}</span>;
}

export function Vocabulary() {
  const { t } = useI18n();
  const { language } = useStudyLanguage();
  const [status, setStatus] = useState("");
  const [kind, setKind] = useState("");
  const [q, setQ] = useState("");
  const [due, setDue] = useState(false);
  const [data, setData] = useState<{ total: number; items: Term[] } | null>(null);

  const statusOptions = [
    { value: "", label: t("vocab.learning") },
    ...[1, 2, 3, 4].map((n) => ({ value: String(n), label: `${n} · ${t(`card.status.${n}` as "card.status.1")}` })),
    { value: String(KNOWN), label: t("vocab.known") },
    { value: String(IGNORED), label: t("vocab.ignored") },
  ];
  const kindLabel = {
    word: t("card.kind.word"),
    phrase: t("card.kind.phrase"),
    phrasal_verb: t("card.kind.phrasal"),
    expression: t("card.kind.expression"),
  };

  useEffect(() => {
    const params: Record<string, string> = { language, limit: "200" };
    if (status) params.status = status;
    if (kind) params.kind = kind;
    if (q) params.q = q;
    if (due) params.due = "true";
    const timer = setTimeout(() => api.terms(params).then(setData), 200);
    return () => clearTimeout(timer);
  }, [language, status, kind, q, due]);

  function replace(term: Term) {
    setData((d) => d && { ...d, items: d.items.map((x) => (x.id === term.id ? term : x)) });
  }

  async function remove(term: Term) {
    await api.deleteTerm(term.id);
    setData((d) => d && { total: d.total - 1, items: d.items.filter((x) => x.id !== term.id) });
  }

  return (
    <div className="page">
      <div className="section-head">
        <h1>{t("vocab.title")}</h1>
        <a className="btn btn-outline" href={`/api/terms/export.csv?language=${language}`}>{t("vocab.export")}</a>
      </div>
      <div className="toolbar">
        <input type="search" placeholder={t("vocab.search")} value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          {statusOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="">{t("vocab.allKinds")}</option>
          <option value="word">{t("vocab.words")}</option>
          <option value="phrase">{t("vocab.phrases")}</option>
          <option value="phrasal_verb">{t("vocab.phrasals")}</option>
          <option value="expression">{t("vocab.expressions")}</option>
        </select>
        <label className="check"><input type="checkbox" checked={due} onChange={(e) => setDue(e.target.checked)} /> {t("vocab.due")}</label>
      </div>

      <div className="card">
        <p className="muted small" style={{ marginTop: 0 }}>{data ? t("vocab.count", { n: data.total }) : t("loading")}</p>
        {data?.items.length === 0 && <div className="empty">{t("vocab.empty")}</div>}
        <div className="vocab-list">
          {data?.items.map((term) => (
            <div key={term.id} className="vocab-row">
              <StatusMini status={term.status} />
              <div className="term" title={term.context}>
                {term.key}
                <small>{kindLabel[term.kind]}</small>
              </div>
              <input
                defaultValue={term.meaning}
                placeholder={t("card.meaning")}
                onBlur={(e) => e.target.value !== term.meaning && api.patchTerm(term.id, { meaning: e.target.value }).then(replace)}
              />
              <select value={term.status} onChange={(e) => api.patchTerm(term.id, { status: Number(e.target.value) }).then(replace)}>
                {statusOptions.filter((o) => o.value).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <button className="btn-ghost" onClick={() => remove(term)}>{t("vocab.delete")}</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
