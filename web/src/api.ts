export type Token = { t: string; ws: string; w: boolean; k: string | null; l: string | null; p?: string | null; s: number };
export type UnitKind = "phrasal_verb" | "phrase" | "expression";
export type Unit = { k: string; kind: UnitKind; sub?: "particle" | "prepositional"; i: number[]; sep: boolean };
export type GrammarMatch = { type: string; s: number; i: number[]; label: string; explanation: string; lemma: string | null };
export type TermKind = "word" | "phrase" | "phrasal_verb" | "expression" | "rule";

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

export type ExtraItem = {
  id: string;
  group: "voice" | "translation" | "dictionary";
  size_mb: number;
  installed: boolean;
  uses_host_ollama: boolean;
  job: { state: "queued" | "installing" | "uninstalling" | "done" | "error"; progress?: number; phase?: string | null; error?: string | null } | null;
};
export type ExtrasStatus = { docker: boolean; items: ExtraItem[]; presets: Record<"light" | "recommended", string[]> };

/** llm: translation model in Ollama; local: LibreTranslate; ai: the configured AI model. */
export type Translator = "llm" | "local" | "ai";

export const IGNORED = -1;
export const KNOWN = 5;

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  // The session ended (hosted service): the app shows the sign-in page again.
  if (res.status === 401 && !path.startsWith("/auth/")) window.dispatchEvent(new Event("glosa:signed-out"));
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

export type Topic = {
  id: number;
  block: string;
  description: string;
  status: "no_visto" | "falla" | "dominado";
  active: boolean;
  streak: number;
  last_practiced: string | null;
};
export type DrillItem = {
  id: number;
  spanish: string;
  topic_ids: number[];
  answer: string;
  correction: string;
  explanation: string;
  examples: string[];
  failed_topic_ids: number[];
  verdict: "correcta" | "con_errores" | null;
  error_tags: string[];
};
export type DrillRound = {
  id: number;
  created_at: string | null;
  corrected_at: string | null;
  book_id: number | null;
  closing_note: string;
  correct: number;
  total: number;
  items?: DrillItem[];
};
export type DrillPrompt = { text: string; custom: boolean; file: string };

export type Account = { id: number; email: string | null; name: string; is_admin: boolean };
export type Invite = { code: string; url: string; note: string; created_at: string | null; used_by: string | null; used_at: string | null };

export const api = {
  drillsStatus: () => request<{ ready: boolean; provider: string; model: string; reason: string | null }>("/drills/status"),
  syllabus: () => request<Topic[]>("/drills/syllabus"),
  patchTopic: (id: number, patch: { status?: Topic["status"]; active?: boolean }) =>
    request<Topic>(`/drills/syllabus/${id}`, json("PATCH", patch)),
  importSyllabus: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ topics: number }>("/drills/syllabus/import", { method: "POST", body: form });
  },
  rounds: () => request<DrillRound[]>("/drills/rounds"),
  newRound: (bookId: number | null) => request<DrillRound>("/drills/rounds", json("POST", { book_id: bookId })),
  round: (id: number) => request<DrillRound>(`/drills/rounds/${id}`),
  deleteRound: (id: number) => request(`/drills/rounds/${id}`, { method: "DELETE" }),
  submitRound: (id: number, answers: string[]) => request<DrillRound>(`/drills/rounds/${id}/answers`, json("POST", { answers })),
  drillStats: () => request<{ errors: { tag: string; count: number }[] }>("/drills/stats"),
  drillPrompts: () => request<Record<"generator" | "corrector", DrillPrompt>>("/drills/prompts"),
  putDrillPrompt: (name: "generator" | "corrector", text: string) => request(`/drills/prompts/${name}`, json("PUT", { text })),
  me: () => request<{ mode: "selfhost" | "hosted"; user: Account | null }>("/auth/me"),
  login: (email: string, password: string) => request<{ user: Account }>("/auth/login", json("POST", { email, password })),
  logout: () => request("/auth/logout", { method: "POST" }),
  checkInvite: (code: string) => request<{ valid: boolean }>(`/auth/invites/${encodeURIComponent(code)}`),
  join: (body: { code: string; email: string; password: string; name: string }) =>
    request<{ user: Account }>("/auth/join", json("POST", body)),
  changePassword: (current: string, next: string) => request("/auth/password", json("POST", { current, new: next })),
  invites: () => request<Invite[]>("/admin/invites"),
  createInvite: (note: string) => request<Invite>("/admin/invites", json("POST", { note })),
  deleteInvite: (code: string) => request(`/admin/invites/${encodeURIComponent(code)}`, { method: "DELETE" }),
  accounts: () => request<(Account & { created_at: string | null; books: number; terms: number })[]>("/admin/users"),

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
  extras: () => request<ExtrasStatus>("/extras"),
  changeExtra: (id: string, action: "install" | "uninstall") => request(`/extras/${id}/${action}`, { method: "POST" }),
  installPreset: (name: string) => request<{ queued: string[] }>(`/extras-preset/${name}`, { method: "POST" }),
  saveKey: (provider: string, key: string) => request(`/ai/keys/${provider}`, json("PUT", { key })),
  deleteKey: (provider: string) => request(`/ai/keys/${provider}`, { method: "DELETE" }),
  testModel: (cfg: { provider: string; model: string; base_url: string | null }) =>
    request<{ ok: boolean; sample: string }>("/ai/test", json("POST", cfg)),
};
