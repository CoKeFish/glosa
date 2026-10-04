/** Pronunciation: human recordings when the dictionary has them, then the local speech
 * engine chosen in the settings, then the browser's own voices. */

import type { Settings } from "./api";

const LOCALES: Record<string, string> = { en: "en-US", es: "es-ES", fr: "fr-FR", de: "de-DE", it: "it-IT", pt: "pt-BR" };

type VoiceConfig = { engine: string; voices: Record<string, string>; preferRecordings: boolean };
let config: VoiceConfig = { engine: "browser", voices: {}, preferRecordings: true };
let current: HTMLAudioElement | null = null;

/** Apply the voice settings (engine and voice per language). */
export function configureVoice(tts: Settings["tts"]) {
  config = { engine: tts.engine, voices: tts.voices ?? {}, preferRecordings: tts.prefer_recordings ?? true };
}

export function voiceFor(engine: string, language: string): string {
  return config.voices[`${engine}:${language}`] ?? "";
}

function bestVoice(language: string): SpeechSynthesisVoice | undefined {
  const locale = LOCALES[language] ?? language;
  const voices = window.speechSynthesis?.getVoices() ?? [];
  const forLanguage = voices.filter((v) => v.lang.toLowerCase().startsWith(language.toLowerCase()));
  // Neural voices ("Natural", "Online", Google) sound far better than the classic ones.
  const quality = (v: SpeechSynthesisVoice) =>
    (/natural|neural|online|google/i.test(v.name) ? 0 : 2) + (v.lang === locale ? 0 : 1);
  return forLanguage.sort((a, b) => quality(a) - quality(b))[0];
}

// Voices load asynchronously in Chrome; asking once warms the list up.
if (typeof window !== "undefined" && "speechSynthesis" in window) {
  window.speechSynthesis.getVoices();
  window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}

export function stop() {
  current?.pause();
  current = null;
  window.speechSynthesis?.cancel();
}

function browserSpeak(text: string, language: string, rate = 0.95) {
  if (!("speechSynthesis" in window)) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = LOCALES[language] ?? language;
  const voice = bestVoice(language);
  if (voice) utterance.voice = voice;
  utterance.rate = rate;
  window.speechSynthesis.speak(utterance);
}

function playUrl(src: string, onFail: () => void) {
  const audio = new Audio(src);
  current = audio;
  audio.onerror = onFail;
  audio.play().catch(onFail);
}

export function engineUrl(engine: string, text: string, language: string, voice = "", nocache = false) {
  const params = new URLSearchParams({ engine, text, language, ...(voice ? { voice } : {}), ...(nocache ? { nocache: "true" } : {}) });
  return `/api/tts?${params}`;
}

/** Speak text with the configured engine; the browser's voice if the engine fails. */
export function speak(text: string, language: string) {
  stop();
  if (config.engine === "browser") return browserSpeak(text, language);
  playUrl(engineUrl(config.engine, text, language, voiceFor(config.engine, language)), () =>
    browserSpeak(text, language),
  );
}

/** A word: its human recording if there is one (and that is preferred), otherwise speak it. */
export function play(url: string | undefined, text: string, language: string) {
  stop();
  if (!url || !config.preferRecordings) return speak(text, language);
  // Through the API: same origin, cached, and it keeps working offline.
  playUrl(`/api/audio?${new URLSearchParams({ url })}`, () => speak(text, language));
}

/** Play a sample with a given engine and voice, for the comparison in the settings.
 * Resolves with the seconds it took the server to produce the audio. */
export async function sample(engine: string, voice: string, text: string, language: string): Promise<number> {
  stop();
  if (engine === "browser") {
    browserSpeak(text, language);
    return 0;
  }
  const t0 = performance.now();
  // no-store: otherwise the browser answers a repeated test from its cache and times nothing.
  const resp = await fetch(engineUrl(engine, text, language, voice, true), { cache: "no-store" });
  if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail ?? resp.statusText);
  const blob = await resp.blob();
  const seconds = (performance.now() - t0) / 1000;
  const audio = new Audio(URL.createObjectURL(blob));
  current = audio;
  await audio.play();
  return seconds;
}

export const canSpeak = () => typeof window !== "undefined" && "speechSynthesis" in window;
