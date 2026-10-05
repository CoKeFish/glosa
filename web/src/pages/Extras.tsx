import { useCallback, useEffect, useState } from "react";
import { api, ExtraItem, ExtrasStatus, Provider } from "../api";
import { useI18n } from "../i18n";

const GROUPS = ["translation", "voice", "dictionary"] as const;
const PRESETS = ["light", "recommended"] as const;

function size(mb: number) {
  return mb >= 1000 ? `${(mb / 1000).toLocaleString(undefined, { maximumFractionDigits: 1 })} GB` : `${mb} MB`;
}

/** Optional components: one-click presets, then each extra with install and uninstall. */
export function Extras() {
  const { t } = useI18n();
  const [status, setStatus] = useState<ExtrasStatus | null>(null);
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState<string | null>(null);

  const load = useCallback(() => api.extras().then(setStatus).catch((e) => setError(e.message)), []);
  useEffect(() => {
    load();
  }, [load]);
  // Poll while something is downloading or being removed.
  const busy = status?.items.some((i) => ["installing", "uninstalling", "queued"].includes(i.job?.state ?? ""));
  useEffect(() => {
    if (!busy) return;
    const timer = setInterval(load, 1500);
    return () => clearInterval(timer);
  }, [busy, load]);

  async function act(item: ExtraItem, action: "install" | "uninstall") {
    setConfirm(null);
    setError("");
    try {
      await api.changeExtra(item.id, action);
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function preset(name: string) {
    setError("");
    try {
      await api.installPreset(name);
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (!status) return <div className="page narrow muted">{error || t("loading")}</div>;
  const byId = Object.fromEntries(status.items.map((i) => [i.id, i]));

  return (
    <div className="page narrow">
      <header className="page-head">
        <h1>{t("ex.title")}</h1>
        <p className="muted">{t("ex.intro")}</p>
      </header>
      {!status.docker && <p className="warn">{t("ex.noDocker")}</p>}
      {error && <p className="error">{error}</p>}

      <section className="card">
        <h2>{t("ex.quick")}</h2>
        <div className="choice-cards">
          {PRESETS.map((name) => {
            const items = status.presets[name].map((id) => byId[id]).filter(Boolean);
            const missing = items.filter((i) => !i.installed);
            const pending = missing.reduce((sum, i) => sum + i.size_mb, 0);
            return (
              <div key={name} className={`choice-card preset ${name === "recommended" ? "on" : ""}`}>
                <strong>{t(`ex.preset.${name}` as "ex.preset.light")}</strong>
                <span className="muted small">{t(`ex.preset.${name}.help` as "ex.preset.light.help")}</span>
                <ul className="preset-list">
                  {items.map((i) => (
                    <li key={i.id} className={i.installed ? "done" : ""}>{t(`ex.item.${i.id}` as "ex.item.voice-kokoro")}</li>
                  ))}
                </ul>
                {missing.length === 0 ? (
                  <span className="pill ok">{t("ex.allInstalled")}</span>
                ) : (
                  <button disabled={!status.docker || busy} onClick={() => preset(name)}>
                    {t("ex.installPreset", { size: size(pending) })}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {GROUPS.map((group) => (
        <section key={group} className="card">
          <h2>{t(`ex.group.${group}` as "ex.group.voice")}</h2>
          <ul className="extras-list">
            {status.items.filter((i) => i.group === group).map((item) => {
              const job = item.job;
              const working = job && ["installing", "uninstalling", "queued"].includes(job.state);
              return (
                <li key={item.id} className="extra">
                  <div className="extra-text">
                    <strong>{t(`ex.item.${item.id}` as "ex.item.voice-kokoro")}</strong>
                    <span className="muted small">{t(`ex.desc.${item.id}` as "ex.desc.voice-kokoro")}</span>
                    {item.uses_host_ollama && <span className="muted small">{t("ex.hostOllama")}</span>}
                    {working && (
                      <div className="progress-line" role="progressbar" aria-valuenow={Math.round((job.progress ?? 0) * 100)}>
                        <span style={{ width: `${Math.max(3, (job.progress ?? 0) * 100)}%` }} />
                        <em>{t(`ex.state.${job.phase ?? job.state}` as "ex.state.installing")} {job.state !== "queued" && `${Math.round((job.progress ?? 0) * 100)} %`}</em>
                      </div>
                    )}
                    {job?.state === "error" && <span className="error small">{job.error}</span>}
                  </div>
                  <div className="extra-actions">
                    <span className="muted small">{size(item.size_mb)}</span>
                    {working ? null : item.installed ? (
                      confirm === item.id ? (
                        <>
                          <button className="btn-danger" onClick={() => act(item, "uninstall")}>{t("ex.confirmRemove")}</button>
                          <button className="btn-ghost" onClick={() => setConfirm(null)}>{t("cancel")}</button>
                        </>
                      ) : (
                        <>
                          <span className="pill ok">{t("ex.installed")}</span>
                          <button className="btn-ghost" disabled={!status.docker && item.group !== "dictionary"} onClick={() => setConfirm(item.id)}>
                            {t("ex.uninstall")}
                          </button>
                        </>
                      )
                    ) : (
                      <button disabled={!status.docker && item.group !== "dictionary"} onClick={() => act(item, "install")}>{t("ex.install")}</button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ))}

      <KeysCard />
    </div>
  );
}

/** Every cloud AI provider's key in one place. Keys are stored encrypted on this computer only. */
function KeysCard() {
  const { t } = useI18n();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState("");
  const load = () => api.providers().then(setProviders).catch(() => {});
  useEffect(() => {
    load();
  }, []);

  async function save(p: Provider) {
    await api.saveKey(p.id, drafts[p.id] ?? "");
    setDrafts((d) => ({ ...d, [p.id]: "" }));
    setSaved(p.id);
    load();
  }

  return (
    <section className="card">
      <h2>{t("ex.keys")}</h2>
      <p className="muted small" style={{ margin: 0 }}>{t("ex.keysHelp")}</p>
      <ul className="extras-list">
        {providers.filter((p) => p.key_env).map((p) => (
          <li key={p.id} className="extra">
            <div className="extra-text">
              <strong>{p.label}</strong>
              {p.key_source === "env" ? (
                <span className="key-status ok">{t("set.keyFromEnv", { key: p.key_env ?? "" })}</span>
              ) : p.key_source === "saved" ? (
                <span className="key-status ok">{t("set.keySaved", { hint: p.key_hint ?? "" })}</span>
              ) : (
                <span className="key-status warn">{t("set.keyMissing", { key: p.key_env ?? "" })}</span>
              )}
              {saved === p.id && <span className="muted small">{t("set.keyStored")}</span>}
            </div>
            {p.key_source !== "env" && (
              <form className="key-row" onSubmit={(e) => { e.preventDefault(); save(p); }}>
                <input
                  type="password"
                  autoComplete="off"
                  placeholder={p.key_source === "saved" ? t("set.keyReplace") : t("set.keyPaste")}
                  value={drafts[p.id] ?? ""}
                  onChange={(e) => setDrafts((d) => ({ ...d, [p.id]: e.target.value }))}
                />
                <button disabled={!(drafts[p.id] ?? "").trim()}>{t("set.keySave")}</button>
                {p.key_source === "saved" && (
                  <button type="button" className="btn-ghost" onClick={() => api.deleteKey(p.id).then(load)}>{t("set.keyRemove")}</button>
                )}
              </form>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
