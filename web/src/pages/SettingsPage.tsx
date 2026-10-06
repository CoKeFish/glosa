import { useEffect, useState } from "react";
import { api, Provider, Settings } from "../api";
import { UsageCard } from "../components/UsageCard";
import { AccountCard, InvitesCard } from "../components/AccountCards";
import { useAuth } from "../auth";
import { VoiceCard } from "../components/VoiceCard";
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

const CUSTOM = "__custom__";

const TRANSLATORS = [
  { id: "llm", label: "set.translatorLlm", help: "set.translatorLlmHelp" },
  { id: "local", label: "set.translatorLocal", help: "set.translatorLocalHelp" },
  { id: "ai", label: "set.translatorAi", help: "set.translatorAiHelp" },
] as const;

export function SettingsPage() {
  const { t, setUiLanguage } = useI18n();
  const { mode, user } = useAuth();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [message, setMessage] = useState("");
  const [testing, setTesting] = useState(false);
  const [keyInput, setKeyInput] = useState("");
  const [models, setModels] = useState<{ list: { id: string; label: string }[]; recommended: string } | null>(null);
  const [modelsError, setModelsError] = useState("");
  const [customModel, setCustomModel] = useState(false);
  const [llm, setLlm] = useState<Awaited<ReturnType<typeof api.translationModels>> | null>(null);
  // Bumped on save: the usage card estimates costs for the saved model.
  const [savedModel, setSavedModel] = useState(0);

  useEffect(() => {
    api.settings().then(setSettings);
    api.providers().then(setProviders);
    api.translationModels().then(setLlm).catch(() => setLlm({ available: false, models: [], recommended: "translategemma:4b" }));
  }, []);

  // Ask the provider which models the key (or local server) offers, whenever that can change.
  const providerId = settings?.["ai.text"].provider;
  const baseUrl = settings?.["ai.text"].base_url ?? null;
  const keyState = providers.find((p) => p.id === providerId)?.key_source;
  useEffect(() => {
    if (!providerId) return;
    let cancelled = false;
    setModels(null);
    setModelsError("");
    const timer = setTimeout(() => {
      api
        .models(providerId, baseUrl)
        .then((r) => !cancelled && setModels({ list: r.models, recommended: r.recommended }))
        .catch((e) => !cancelled && setModelsError(t("set.modelsUnavailable", { reason: (e as Error).message })));
    }, 400);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [providerId, baseUrl, keyState, t]);

  if (!settings) return <div className="page narrow muted">{t("loading")}</div>;
  const ai = settings["ai.text"];
  const translation = settings.translation;
  const provider = providers.find((p) => p.id === ai.provider);

  const update = <K extends keyof Settings>(key: K, value: Settings[K]) => setSettings({ ...settings, [key]: value });

  function chooseProvider(id: string) {
    const p = providers.find((x) => x.id === id);
    setCustomModel(false);
    update("ai.text", { provider: id, model: p?.default_model ?? "", base_url: p?.default_base_url ?? null });
  }

  async function save() {
    try {
      const saved = await api.saveSettings(settings!);
      setSettings(saved);
      setSavedModel((n) => n + 1);
      setUiLanguage(saved.ui_language.value);
      setMessage(t("set.saved"));
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  async function saveKey() {
    if (!provider) return;
    try {
      await api.saveKey(provider.id, keyInput);
      setKeyInput("");
      setProviders(await api.providers());
      setMessage(t("set.keyStored"));
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  async function removeKey() {
    if (!provider) return;
    await api.deleteKey(provider.id);
    setProviders(await api.providers());
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
        {mode === "hosted" && <AccountCard />}
        {mode === "hosted" && user?.is_admin && <InvitesCard />}
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
        </section>

        <section className="card">
          <h2>{t("set.translation")}</h2>
          <div className="choice-cards three">
            {TRANSLATORS.map(({ id, label, help }) => (
              <label key={id} className={`choice-card ${translation.provider === id ? "on" : ""}`}>
                <input
                  type="radio"
                  name="translator"
                  checked={translation.provider === id}
                  onChange={() => update("translation", { ...translation, provider: id })}
                />
                <strong>{t(label)}</strong>
                <span className="muted small">{t(help)}</span>
              </label>
            ))}
          </div>
          {translation.provider === "llm" && (
            <>
              {llm && !llm.available && (
                <p className="warn small" style={{ margin: 0 }}>{t("set.llmMissing", { model: llm.recommended })}</p>
              )}
              {llm?.available && (
                <label>
                  {t("set.llmModel")}
                  <select
                    value={translation.llm_model}
                    onChange={(e) => update("translation", { ...translation, llm_model: e.target.value })}
                  >
                    {[...new Set([translation.llm_model, ...llm.models])].map((m) => (
                      <option key={m} value={m}>
                        {m}{m === llm.recommended ? ` — ${t("set.llmRecommended")}` : ""}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {llm?.available && !llm.models.includes(llm.recommended) && (
                <p className="warn small" style={{ margin: 0 }}>{t("set.llmNotInstalled", { model: llm.recommended })}</p>
              )}
              <label className="check">
                <input
                  type="checkbox"
                  checked={translation.use_gpu}
                  onChange={(e) => update("translation", { ...translation, use_gpu: e.target.checked })}
                />
                {t("set.llmGpu")}
              </label>
            </>
          )}
          {translation.provider === "ai" && !provider?.key_configured && provider?.key_env && (
            <p className="warn small" style={{ margin: 0 }}>{t("set.aiNeedsKey")}</p>
          )}
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
          <label className="check">
            <input
              type="checkbox"
              checked={settings.reader.auto_play}
              onChange={(e) => update("reader", { ...settings.reader, auto_play: e.target.checked })}
            />
            {t("set.autoPlay")}
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
            <div className="key-field">
              <p className="field-label">{t("set.apiKey")}</p>
              {provider.key_source === "env" ? (
                <span className="key-status ok">{t("set.keyFromEnv", { key: provider.key_env })}</span>
              ) : provider.key_source === "saved" ? (
                <div className="key-row">
                  <span className="key-status ok">{t("set.keySaved", { hint: provider.key_hint ?? "" })}</span>
                  <button className="btn-ghost" onClick={removeKey}>{t("set.keyRemove")}</button>
                </div>
              ) : (
                <span className="key-status warn">{t("set.keyMissing", { key: provider.key_env })}</span>
              )}
              {provider.key_source !== "env" && (
                <form
                  className="key-row"
                  onSubmit={(e) => {
                    e.preventDefault();
                    saveKey();
                  }}
                >
                  <input
                    type="password"
                    autoComplete="off"
                    placeholder={provider.key_source === "saved" ? t("set.keyReplace") : t("set.keyPaste")}
                    value={keyInput}
                    onChange={(e) => setKeyInput(e.target.value)}
                  />
                  <button disabled={!keyInput.trim()}>{t("set.keySave")}</button>
                </form>
              )}
              {provider.key_source !== "env" && <span className="muted small">{t("set.keyHelp")}</span>}
            </div>
          )}
          <label>
            {t("set.model")}
            {models && !customModel ? (
              <select
                value={ai.model}
                onChange={(e) =>
                  e.target.value === CUSTOM ? setCustomModel(true) : update("ai.text", { ...ai, model: e.target.value })
                }
              >
                {!models.list.some((m) => m.id === ai.model) && ai.model && <option value={ai.model}>{ai.model}</option>}
                {!ai.model && <option value="">{t("set.modelPick")}</option>}
                {models.list.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}{m.id === models.recommended ? ` — ${t("set.recommended")}` : ""}
                  </option>
                ))}
                <option value={CUSTOM}>{t("set.modelOther")}</option>
              </select>
            ) : (
              <input
                value={ai.model}
                placeholder="claude-opus-5-5, llama3.1…"
                onChange={(e) => update("ai.text", { ...ai, model: e.target.value })}
              />
            )}
            {modelsError && <span className="warn small" style={{ fontWeight: 400 }}>{modelsError}</span>}
            {customModel && models && (
              <button type="button" className="btn-ghost" style={{ alignSelf: "flex-start" }} onClick={() => setCustomModel(false)}>
                {t("set.modelBackToList")}
              </button>
            )}
          </label>
          {provider?.base_url_editable && (
            <label>
              {t("set.serverUrl")}
              <input value={ai.base_url ?? ""} onChange={(e) => update("ai.text", { ...ai, base_url: e.target.value || null })} />
            </label>
          )}
        </section>

        <VoiceCard settings={settings} onChange={(tts) => update("tts", tts)} />

        <UsageCard
          settings={settings}
          modelKey={`${ai.provider}/${ai.model}/${savedModel}`}
          onPrice={(model, price) =>
            price && update("ai.prices", { ...settings["ai.prices"], [model]: price })
          }
        />

        <div className="actions">
          <button onClick={save}>{t("set.save")}</button>
          <button className="btn-outline" onClick={test} disabled={testing}>{testing ? t("set.testing") : t("set.test")}</button>
          {message && <span className="small">{message}</span>}
        </div>
      </div>
    </div>
  );
}
