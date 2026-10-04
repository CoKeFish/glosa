import { useEffect, useState } from "react";
import { Link } from "react-router";
import { api, Term } from "../api";
import { useI18n } from "../i18n";
import { useStudyLanguage } from "../Layout";

export function Review() {
  const { t } = useI18n();
  const { language } = useStudyLanguage();
  const [queue, setQueue] = useState<Term[] | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [done, setDone] = useState(0);

  useEffect(() => {
    api.reviewQueue(language).then(setQueue);
    setDone(0);
  }, [language]);

  const card = queue?.[0];

  async function answer(correct: boolean) {
    if (!card) return;
    const { still_due } = await api.answer(card.id, correct);
    // A term stays in the session until it is answered right twice in a row.
    setQueue((q) => (q ? [...q.slice(1), ...(still_due ? [card] : [])] : q));
    if (!still_due) setDone((n) => n + 1);
    setRevealed(false);
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!card) return;
      if (e.key === " " && !revealed) {
        e.preventDefault();
        setRevealed(true);
      } else if (revealed && e.key === "1") answer(false);
      else if (revealed && e.key === "2") answer(true);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (!queue) return <div className="page narrow muted">{t("loading")}</div>;
  if (!card)
    return (
      <div className="page narrow">
        <h1>{t("review.title")}</h1>
        <div className="card empty">
          <p>{done ? t("review.done", { n: done }) : t("review.none")}</p>
          <Link className="btn" to="/">{t("review.backToReading")}</Link>
        </div>
      </div>
    );

  return (
    <div className="page narrow">
      <h1>{t("review.title")}</h1>
      <div className="review-progress">
        <span>{t("review.inSession", { n: queue.length })}</span>
        <span>{t("review.completed", { n: done })}</span>
      </div>
      <div className="flashcard" onClick={() => setRevealed(true)}>
        <p className="term">{card.key}</p>
        {card.kind !== "word" && (
          <div>
            <span className={`tag ${card.kind === "phrasal_verb" ? "phrasal" : card.kind === "expression" ? "expression" : "phrase"}`}>
              {card.kind === "phrasal_verb"
                ? t("card.kind.phrasal")
                : card.kind === "expression"
                  ? t("card.kind.expression")
                  : t("card.kind.phrase")}
            </span>
          </div>
        )}
        {revealed ? (
          <>
            <p className="meaning">{card.meaning || <span className="muted">{t("review.noMeaning")}</span>}</p>
            {card.context && <p className="context">{card.context}</p>}
            {card.notes && <p className="context small">{card.notes}</p>}
          </>
        ) : (
          <p className="muted small">{t("review.reveal")}</p>
        )}
      </div>
      {revealed && (
        <div className="answer-bar">
          <button className="no" onClick={() => answer(false)}>{t("review.no")} <kbd>1</kbd></button>
          <button onClick={() => answer(true)}>{t("review.yes")} <kbd>2</kbd></button>
        </div>
      )}
    </div>
  );
}
