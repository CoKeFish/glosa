import { useEffect, useState } from "react";
import { api, Provider, Settings } from "../api";
import { UI_LANGUAGES, useI18n } from "../i18n";

// Languages meanings and explanations can be written in. Grammar explanations exist in
// Spanish and English; the dictionary and the AI handle the rest.
const MEANING_LANGUAGES = [
  { code: "es", name: "Español" },
  { code: "en", name: "English" },
  { code: "pt", name: "Português" },
  { code: "fr", name: "Français" },
  { code: "de", name: "Deutsch" },
  { code: "it", name: "Italiano" },
];

export function SettingsPage() {
  const { t, setUiLanguage } = useI18n();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [message, setMessage] = useState("");
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    api.settings().then(setSettings);
    api.providers().then(setProviders);
  }, []);

  if (!settings) return <div className="page narrow muted">{t("loading")}</div>;
  const ai = settings["ai.text"];
  const provider = providers.find((p) => p.id === ai.provider);

  const update = <K extends keyof Settings>(key: K, value: Settings[K]) => setSettings({ ...settings, [key]: value });

  function chooseProvider(id: string) {
    const p = providers.find((x) => x.id === id);
    update("ai.text", { provider: id, model: p?.default_model ?? "", base_url: p?.default_base_url ?? null });
  }

  async function save() {
    try {
      const saved = await api.saveSettings(settings!);
      setSettings(saved);
      setUiLanguage(saved.ui_language.value);
      setMessage(t("set.saved"));
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  async function test() {
    setTesting(true);
    setMessage("");
    try {
      const r = await api.testModel(ai);
      setMessage(t("set.testOk", { sample: r.sample }));
    } catch (e) {
      setMessage(`Error: ${(e as Error).message}`);
    } finally {
      setTesting(false);
    }
  }

  return (
    <div className="page narrow">
      <h1>{t("set.title")}</h1>
      <div className="settings-stack">
        <section className="card">
          <h2>{t("set.languages")}</h2>
          <label>
            {t("set.uiLanguage")}
            <select value={settings.ui_language.value} onChange={(e) => update("ui_language", { value: e.target.value })}>
              {UI_LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
            </select>
          </label>
          <label>
            {t("set.meaningLanguage")}
            <select value={settings.native_language.value} onChange={(e) => update("native_language", { value: e.target.value })}>
              {MEANING_LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
            </select>
            <span className="muted small" style={{ fontWeight: 400 }}>{t("set.meaningHelp")}</span>
          </label>
          <p className="muted small" style={{ margin: 0 }}>{t("set.studyHelp")}</p>
          <label>
            {t("set.translator")}
            <select
              value={settings.translation.provider}
              onChange={(e) => update("translation", { provider: e.target.value as "local" | "ai" })}
            >
              <option value="local">{t("set.translatorLocal")}</option>
              <option value="ai">{t("set.translatorAi")}</option>
            </select>
            <span className="muted small" style={{ fontWeight: 400 }}>{t("set.translatorHelp")}</span>
          </label>
        </section>

        <section className="card">
          <h2>{t("set.reading")}</h2>
          <label className="check">
            <input
              type="checkbox"
              checked={settings.reader.page_marks_known}
              onChange={(e) => update("reader", { ...settings.reader, page_marks_known: e.target.checked })}
            />
            {t("set.pageKnown")}
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={settings.reader.click_saves}
              onChange={(e) => update("reader", { ...settings.reader, click_saves: e.target.checked })}
            />
            {t("set.clickSaves")}
          </label>
          <label>
            {t("set.sessionSize")}
            <input
              type="number"
              min={5}
              max={200}
              value={settings.review.session_size}
              onChange={(e) => update("review", { session_size: Number(e.target.value) })}
            />
          </label>
        </section>

        <section className="card">
          <h2>{t("set.ai")}</h2>
          <p className="muted small" style={{ margin: 0 }}>{t("set.aiHelp")}</p>
          <label>
            {t("set.provider")}
            <select value={ai.provider} onChange={(e) => chooseProvider(e.target.value)}>
              {providers.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
            </select>
          </label>
          {provider?.key_env && (
            <span className={`key-status ${provider.key_configured ? "ok" : "warn"}`}>
              {t(provider.key_configured ? "set.keyOk" : "set.keyMissing", { key: provider.key_env })}
            </span>
          )}
          <label>
            {t("set.model")}
            <input value={ai.model} placeholder="claude-opus-5-5, llama3.1…" onChange={(e) => update("ai.text", { ...ai, model: e.target.value })} />
          </label>
          {provider?.base_url_editable && (
            <label>
              {t("set.serverUrl")}
              <input value={ai.base_url ?? ""} onChange={(e) => update("ai.text", { ...ai, base_url: e.target.value || null })} />
            </label>
          )}
        </section>

        <div className="actions">
          <button onClick={save}>{t("set.save")}</button>
          <button className="btn-outline" onClick={test} disabled={testing}>{testing ? t("set.testing") : t("set.test")}</button>
          {message && <span className="small">{message}</span>}
        </div>
      </div>
    </div>
  );
}
