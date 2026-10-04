import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { api, Book } from "../api";
import { Cover } from "../Cover";
import { useI18n } from "../i18n";

export function BookPage() {
  const { t } = useI18n();
  const { bookId } = useParams();
  const navigate = useNavigate();
  const [book, setBook] = useState<Book | null>(null);
  const [reanalyzing, setReanalyzing] = useState(false);

  const load = useCallback(() => api.book(Number(bookId)).then(setBook), [bookId]);
  useEffect(() => {
    load();
  }, [load]);

  if (!book) return <div className="page muted">{t("loading")}</div>;
  const current = book.sections.find((s) => s.position === book.current_position) ?? book.sections[0];
  const words = book.sections.reduce((n, s) => n + s.word_count, 0);

  async function remove() {
    if (!book || !window.confirm(t("book.confirmDelete", { title: book.title }))) return;
    await api.deleteBook(book.id);
    navigate("/");
  }

  async function reanalyze() {
    if (!book) return;
    setReanalyzing(true);
    try {
      await api.reanalyze(book.id);
      await load();
    } finally {
      setReanalyzing(false);
    }
  }

  return (
    <div className="page">
      <div className="hero book-hero">
        <Cover title={book.title} />
        <div>
          <p className="muted small"><Link to="/">{t("nav.library")}</Link> / {book.title}</p>
          <h1>{book.title}</h1>
          <p className="muted">
            {book.sections.length === 1 ? t("lib.lesson") : t("lib.lessons", { n: book.sections.length })} ·{" "}
            {t("lib.words", { n: words.toLocaleString() })}
          </p>
          {current && (
            <Link className="btn" to={`/read/${current.id}`}>
              {book.current_position > 0 ? t("book.continue") : t("book.start")}
            </Link>
          )}
        </div>
      </div>

      <div className="section-head">
        <h2>{t("book.lessons")}</h2>
        <div className="actions">
          <button className="btn-outline" onClick={reanalyze} disabled={reanalyzing}>
            {reanalyzing ? t("book.reanalyzing") : t("book.reanalyze")}
          </button>
          <button className="btn-danger" onClick={remove}>{t("book.delete")}</button>
        </div>
      </div>
      <div className="card lessons">
        {book.sections.map((s) => (
          <Link key={s.id} to={`/read/${s.id}`} className={`lesson-row ${s.position === book.current_position ? "current" : ""}`}>
            <span className="num">{s.position + 1}</span>
            <span className="title">{s.title}</span>
            <span className="muted small">{t("lib.words", { n: s.word_count.toLocaleString() })}</span>
            <span className="new-badge">{t("book.newPct", { n: s.new_pct })}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
