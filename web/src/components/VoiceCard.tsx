import { useEffect, useState } from "react";
import { api, Settings } from "../api";
import { useI18n } from "../i18n";
import { Speaker } from "../icons";
import { useStudyLanguage } from "../Layout";
import { configureVoice, sample } from "../speech";

type Engine = Awaited<ReturnType<typeof api.ttsEngines>>[number];

const SAMPLES: Record<string, string> = {
  en: "In relating the circumstances which have led to my confinement, I am aware of a natural doubt.",
  es: "Al relatar las circunstancias que me han llevado a mi encierro, soy consciente de una duda natural.",
};

type Props = { settings: Settings; onChange: (tts: Settings["tts"]) => void };

/** Choose and compare speech engines: play the same sentence with each and see how long it took. */
export function VoiceCard({ settings, onChange }: Props) {
  const { t } = useI18n();
  const { language } = useStudyLanguage();
  const [engines, setEngines] = useState<Engine[] | null>(null);
  const [text, setText] = useState(SAMPLES[language] ?? SAMPLES.en);
  const [timing, setTiming] = useState<Record<string, string>>({});
  const tts = settings.tts;

  useEffect(() => {
    api.ttsEngines(language).then(setEngines).catch(() => setEngines([]));
  }, [language]);

  const voiceOf = (e: Engine) => tts.voices[`${e.id}:${language}`] || e.default_voice;

  function update(next: Settings["tts"]) {
    configureVoice(next); // takes effect in the reader right away, saved with "Guardar cambios"
    onChange(next);
  }

  async function test(engineId: string, voice: string) {
    setTiming((m) => ({ ...m, [engineId]: t("voice.generating") }));
    try {
      const seconds = await sample(engineId, voice, text, language);
      setTiming((m) => ({ ...m, [engineId]: engineId === "browser" ? t("voice.instant") : t("voice.took", { s: seconds.toFixed(2) }) }));
    } catch (e) {
      setTiming((m) => ({ ...m, [engineId]: (e as Error).message }));
    }
  }

  const options: { id: string; label: string; available: boolean; voices: { id: string; label: string }[]; voice: string; help: string }[] = [
    ...(engines ?? []).map((e) => ({
      id: e.id, label: e.label, available: e.available, voices: e.voices, voice: voiceOf(e),
      help: t(`voice.help.${e.id}` as "voice.help.kokoro"),
    })),
    { id: "browser", label: t("voice.browser"), available: true, voices: [], voice: "", help: t("voice.help.browser") },
  ];

  return (
    <section className="card">
      <h2>{t("voice.title")}</h2>
      <p className="muted small" style={{ margin: 0 }}>{t("voice.intro")}</p>
      <label>
        {t("voice.sampleText")}
        <input value={text} onChange={(e) => setText(e.target.value)} />
      </label>
      {!engines && <p className="muted small">{t("loading")}</p>}
      <div className="voice-list">
        {options.map((o) => (
          <div key={o.id} className={`voice-option ${tts.engine === o.id ? "on" : ""} ${o.available ? "" : "off"}`}>
            <label className="voice-pick">
              <input
                type="radio"
                name="tts-engine"
                checked={tts.engine === o.id}
                disabled={!o.available}
                onChange={() => update({ ...tts, engine: o.id })}
              />
              <span>
                <strong>{o.label}</strong>
                <span className="muted small">{o.available ? o.help : t("voice.unavailable")}</span>
              </span>
            </label>
            <div className="voice-controls">
              {o.voices.length > 0 && (
                <select
                  value={o.voice}
                  onChange={(e) => update({ ...tts, voices: { ...tts.voices, [`${o.id}:${language}`]: e.target.value } })}
                >
                  {o.voices.map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
                </select>
              )}
              <button className="btn-outline" disabled={!o.available} onClick={() => test(o.id, o.voice)}>
                <Speaker size={16} /> {t("voice.try")}
              </button>
              {timing[o.id] && <span className="muted small">{timing[o.id]}</span>}
            </div>
          </div>
        ))}
      </div>
      <label className="check">
        <input
          type="checkbox"
          checked={tts.prefer_recordings ?? true}
          onChange={(e) => update({ ...tts, prefer_recordings: e.target.checked })}
        />
        {t("voice.preferRecordings")}
      </label>
    </section>
  );
}
