import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { api, BookSummary } from "../api";
import { Cover } from "../Cover";
import { useI18n } from "../i18n";
import { useStudyLanguage } from "../Layout";

export function Library() {
  const { t } = useI18n();
  const { language, languages } = useStudyLanguage();
  const navigate = useNavigate();
  const [books, setBooks] = useState<BookSummary[] | null>(null);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [importLanguage, setImportLanguage] = useState(language);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.books().then(setBooks);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const form = new FormData();
    form.set("language", importLanguage);
    form.set("title", title);
    form.set("text", text);
    if (file) form.set("file", file);
    setBusy(true);
    try {
      const { id } = await api.importBook(form);
      navigate(`/books/${id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const shown = books?.filter((b) => b.language === language) ?? [];

  return (
    <div className="page">
      <div className="section-head">
        <h1>{t("lib.title")}</h1>
        <a href="#import">{t("lib.import")}</a>
      </div>
      {books && shown.length === 0 && <div className="card empty">{t("lib.empty")}</div>}
      <div className="shelf">
        {shown.map((b) => (
          <Link key={b.id} to={`/books/${b.id}`} className="book-card">
            <Cover title={b.title} />
            <h3>{b.title}</h3>
            <div className="book-meta">
              <span>{t("lib.words", { n: b.words.toLocaleString() })}</span>
              <span>{b.sections === 1 ? t("lib.lesson") : t("lib.lessons", { n: b.sections })}</span>
            </div>
          </Link>
        ))}
      </div>

      <div className="section-head" id="import">
        <h2>{t("lib.import")}</h2>
      </div>
      <form className="card import-grid" onSubmit={submit}>
        <label>
          {t("lib.language")}
          <select value={importLanguage} onChange={(e) => setImportLanguage(e.target.value)}>
            {(languages.length ? languages : [{ code: "en", name: "English" }]).map((l) => (
              <option key={l.code} value={l.code}>{l.name}</option>
            ))}
          </select>
        </label>
        <label>
          {t("lib.titleField")}
          <input value={title} placeholder={t("lib.titlePlaceholder")} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label className="dropzone full">
          <input type="file" accept=".epub,.txt,.md,.html,.htm" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          {file ? <strong>{file.name}</strong> : <><strong>{t("lib.chooseFile")}</strong> · {t("lib.formats")}</>}
        </label>
        <label className="full">
          {t("lib.paste")}
          <textarea rows={6} value={text} onChange={(e) => setText(e.target.value)} disabled={!!file} />
        </label>
        {error && <p className="error full">{error}</p>}
        <div className="full">
          <button disabled={busy || (!file && !text.trim())}>{busy ? t("lib.analyzing") : t("lib.create")}</button>
        </div>
      </form>
    </div>
  );
}
