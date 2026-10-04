/** Pronunciation: recorded audio when the dictionary has it, the browser's voices otherwise. */

const LOCALES: Record<string, string> = { en: "en-US", es: "es-ES", fr: "fr-FR", de: "de-DE", it: "it-IT", pt: "pt-BR" };

let current: HTMLAudioElement | null = null;

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

/** Speak text with the browser's text-to-speech. */
export function speak(text: string, language: string, rate = 0.95) {
  if (!("speechSynthesis" in window)) return;
  stop();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = LOCALES[language] ?? language;
  const voice = bestVoice(language);
  if (voice) utterance.voice = voice;
  utterance.rate = rate;
  window.speechSynthesis.speak(utterance);
}

/** Play a recording; fall back to text-to-speech if it can't be played. */
export function play(url: string | undefined, text: string, language: string) {
  stop();
  if (!url) return speak(text, language);
  // Through the API: same origin, cached, and it keeps working offline.
  const audio = new Audio(`/api/audio?${new URLSearchParams({ url })}`);
  current = audio;
  audio.play().catch(() => speak(text, language));
}

export const canSpeak = () => typeof window !== "undefined" && "speechSynthesis" in window;
