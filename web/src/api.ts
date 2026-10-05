export type Token = { t: string; ws: string; w: boolean; k: string | null; l: string | null; p?: string | null; s: number };
export type UnitKind = "phrasal_verb" | "phrase" | "expression";
export type Unit = { k: string; kind: UnitKind; sub?: "particle" | "prepositional"; i: number[]; sep: boolean };
export type GrammarMatch = { type: string; s: number; i: number[]; label: string; explanation: string; lemma: string | null };
export type TermKind = "word" | "phrase" | "phrasal_verb" | "expression";

export type Term = {
  id: number;
  language: string;
  key: string;
  kind: TermKind;
  status: number;
  meaning: string;
  notes: string;
  tags: string[];
  context: string;
  srs_due: string | null;
  streak: number;
};

export type Section = {
  id: number;
  title: string;
  position: number;
  book: { id: number; title: string; language: string; sections: number };
  prev_id: number | null;
  next_id: number | null;
  tokens: Token[];
  units: Unit[];
  grammar: GrammarMatch[];
  terms: Record<string, Term>;
};

export type BookSummary = {
  id: number;
  title: string;
  language: string;
  sections: number;
  words: number;
  current_position: number;
};
export type Book = {
  id: number;
  title: string;
  language: string;
  current_position: number;
  sections: { id: number; position: number; title: string; word_count: number; new_words: number; new_pct: number }[];
};

export type DictionaryResult = {
  pronunciation: { ipa: string[]; audio: { url: string; accent: string }[] } | null;
  translations: { text: string; sense: string; term: string; part_of_speech: string; score: number; fits: boolean }[];
  sentence_translation: string;
  results: { term: string; source: string; entries: { part_of_speech: string; definitions: string[]; examples: string[] }[] }[];
  links: { name: string; url: string }[];
  errors: string[];
};

export type Provider = {
  id: string;
  label: string;
  key_env: string | null;
  key_configured: boolean;
  key_source: "env" | "saved" | null;
  key_hint: string | null;
  default_model: string;
  default_base_url: string | null;
  base_url_editable: boolean;
};

export type UsageReport = {
  days: number;
  calls: number;
  total_cost: number;
  unpriced_calls: number;
  model: { provider: string; model: string; price: { input: number; output: number } | null; custom: boolean };
  features: {
    feature: "translate" | "explain" | "expressions" | "grammar";
    calls: number;
    measured: boolean;
    avg_input_tokens: number;
    avg_output_tokens: number;
    cost_per_call: number | null;
  }[];
};

export type Settings = {
  ui_language: { value: string };
  native_language: { value: string };
  reader: { page_marks_known: boolean; click_saves: boolean; auto_play: boolean };
  review: { session_size: number };
  translation: { provider: Translator; llm_model: string; use_gpu: boolean };
  "ai.prices": Record<string, { input: number; output: number }>;
  tts: { engine: string; voices: Record<string, string>; prefer_recordings?: boolean };
  "ai.text": { provider: string; model: string; base_url: string | null };
};

/** llm: translation model in Ollama; local: LibreTranslate; ai: the configured AI model. */
export type Translator = "llm" | "local" | "ai";

export const IGNORED = -1;
export const KNOWN = 5;

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json();
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  languages: () => request<{ code: string; name: string }[]>("/languages"),
  books: () => request<BookSummary[]>("/books"),
  book: (id: number) => request<Book>(`/books/${id}`),
  deleteBook: (id: number) => request(`/books/${id}`, { method: "DELETE" }),
  importBook: (form: FormData) => request<{ id: number }>("/books/import", { method: "POST", body: form }),
  setPosition: (bookId: number, position: number) => request(`/books/${bookId}/position`, json("POST", { position })),
  section: (id: number) => request<Section>(`/sections/${id}`),
  stats: (language: string) =>
    request<{ known_words: number; learning: number; total_saved: number }>(`/stats?language=${language}`),

  saveTerm: (t: { language: string; key: string; kind: TermKind; status?: number; meaning?: string; notes?: string; context?: string }) =>
    request<Term>("/terms", json("PUT", t)),
  patchTerm: (id: number, patch: Partial<Pick<Term, "status" | "meaning" | "notes" | "tags">>) =>
    request<Term>(`/terms/${id}`, json("PATCH", patch)),
  deleteTerm: (id: number) => request(`/terms/${id}`, { method: "DELETE" }),
  terms: (params: Record<string, string>) =>
    request<{ total: number; items: Term[] }>(`/terms?${new URLSearchParams(params)}`),
  markKnown: (language: string, keys: string[]) =>
    request<{ created: string[] }>("/terms/mark-known", json("POST", { language, keys })),
  undoKnown: (language: string, keys: string[]) => request("/terms/undo-known", json("POST", { language, keys })),

  reviewQueue: (language: string) => request<Term[]>(`/review/queue?language=${language}`),
  answer: (id: number, correct: boolean) =>
    request<{ term: Term; still_due: boolean }>(`/review/${id}/answer`, json("POST", { correct })),

  dictionary: (q: { language: string; term: string; lemma?: string | null; surface: string; context: string; kind: TermKind }) =>
    request<DictionaryResult>(
      `/dictionary?${new URLSearchParams({
        language: q.language,
        term: q.term,
        surface: q.surface,
        context: q.context,
        kind: q.kind,
        ...(q.lemma && q.lemma !== q.term ? { lemma: q.lemma } : {}),
      })}`,
    ),
  /** context: the sentence the text comes from, so the translator picks the sense it has there. */
  translateText: (language: string, text: string, provider?: Translator, context = "") =>
    request<{ translation: string | null; provider: Translator; message?: string }>(
      "/translate",
      json("POST", { language, text, provider, context }),
    ),
  translationModels: () =>
    request<{ available: boolean; models: string[]; recommended: string }>("/translation/models"),
  findExpressions: (language: string, sentence: string, known: string[]) =>
    request<{ expressions: { text: string; base: string; meaning: string }[] }>(
      "/ai/expressions",
      json("POST", { language, sentence, known }),
    ),
  explainGrammar: (language: string, sentence: string, structures: string[]) =>
    request<{ explanation: string }>("/ai/grammar", json("POST", { language, sentence, structures })),
  reanalyze: (bookId: number) => request<{ sections: number }>(`/books/${bookId}/reanalyze`, { method: "POST" }),
  explain: (body: { language: string; term: string; kind: TermKind; context: string }) =>
    request<{ translation: string; explanation: string; is_phrasal_verb: boolean }>("/ai/explain", json("POST", body)),

  settings: () => request<Settings>("/settings"),
  saveSettings: (s: Partial<Settings>) => request<Settings>("/settings", json("PUT", s)),
  providers: () => request<Provider[]>("/ai/providers"),
  models: (provider: string, baseUrl: string | null) =>
    request<{ models: { id: string; label: string }[]; recommended: string }>(
      `/ai/models?${new URLSearchParams({ provider, ...(baseUrl ? { base_url: baseUrl } : {}) })}`,
    ),
  usage: () => request<UsageReport>("/ai/usage"),
  ttsEngines: (language: string) =>
    request<
      { id: string; label: string; available: boolean; voices: { id: string; label: string }[]; default_voice: string }[]
    >(`/tts/engines?language=${language}`),
  saveKey: (provider: string, key: string) => request(`/ai/keys/${provider}`, json("PUT", { key })),
  deleteKey: (provider: string) => request(`/ai/keys/${provider}`, { method: "DELETE" }),
  testModel: (cfg: { provider: string; model: string; base_url: string | null }) =>
    request<{ ok: boolean; sample: string }>("/ai/test", json("POST", cfg)),
};
