import { createContext, useContext, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router";
import { api } from "./api";
import { useI18n } from "./i18n";
import { configureVoice } from "./speech";
import wordmark from "./wordmark.svg?raw";

type LanguageContext = { language: string; setLanguage: (code: string) => void; languages: { code: string; name: string }[] };
const Ctx = createContext<LanguageContext>({ language: "en", setLanguage: () => {}, languages: [] });

/** The language being studied, for the pages that are not tied to a book (vocabulary, review). */
export const useStudyLanguage = () => useContext(Ctx);

function readStored(): string {
  try {
    return localStorage.getItem("glosa.language") ?? "en";
  } catch {
    return "en";
  }
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState(readStored);
  const [languages, setLanguages] = useState<{ code: string; name: string }[]>([]);

  useEffect(() => {
    api.languages().then(setLanguages).catch(() => {});
    api.settings().then((s) => configureVoice(s.tts)).catch(() => {});
  }, []);

  const setLanguage = (code: string) => {
    setLanguageState(code);
    try {
      localStorage.setItem("glosa.language", code);
    } catch {
      /* storage unavailable */
    }
  };

  return <Ctx.Provider value={{ language, setLanguage, languages }}>{children}</Ctx.Provider>;
}

export function Layout() {
  const { t } = useI18n();
  const { language, setLanguage, languages } = useStudyLanguage();
  const location = useLocation();
  const [known, setKnown] = useState<number | null>(null);

  useEffect(() => {
    api.stats(language).then((s) => setKnown(s.known_words)).catch(() => setKnown(null));
  }, [language, location.pathname]);

  return (
    <>
      <header className="topbar">
        <NavLink to="/" className="brand" aria-label="glosa">
          <span className="wordmark" aria-hidden="true" dangerouslySetInnerHTML={{ __html: wordmark }} />
        </NavLink>
        <nav>
          <NavLink to="/" end>{t("nav.library")}</NavLink>
          <NavLink to="/vocabulary">{t("nav.vocabulary")}</NavLink>
          <NavLink to="/review">{t("nav.review")}</NavLink>
          <NavLink to="/extras">{t("nav.extras")}</NavLink>
          <NavLink to="/settings">{t("nav.settings")}</NavLink>
        </nav>
        <div className="topbar-right">
          {known !== null && (
            <span className="pill-stat" title={t("nav.known")}>
              <span className="dot" /> {known.toLocaleString()}
            </span>
          )}
          <select className="lang-select" value={language} onChange={(e) => setLanguage(e.target.value)} aria-label={t("nav.studying")} title={t("nav.studying")}>
            {(languages.length ? languages : [{ code: "en", name: "English" }]).map((l) => (
              <option key={l.code} value={l.code}>{l.name}</option>
            ))}
          </select>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
    </>
  );
}
