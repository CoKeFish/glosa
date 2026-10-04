import { Section, Term, TermKind, Token } from "./api";

/** What the term panel is showing: one word, a saved phrase, or a phrasal verb. */
export type Selection = {
  kind: TermKind;
  key: string;
  tokens: number[];
  lemma?: string | null;
  pos?: string | null;
  sub?: "particle" | "prepositional";
  /** When a unit was selected by clicking one of its words, that word alone. */
  word?: Selection;
  /** Chosen with a mouse click (not keyboard navigation): clicking a new word means "I don't know it". */
  clicked?: boolean;
};

/** Longer selections (whole sentences) are translated, not saved: like LingQ, only short
 * expressions that recur across texts are worth reviewing. */
export const MAX_SAVED_PHRASE_WORDS = 8;

export function wordSelection(tokens: Token[], i: number): Selection | null {
  const t = tokens[i];
  if (!t?.w || !t.k) return null;
  return { kind: "word", key: t.k, tokens: [i], lemma: t.l, pos: t.p };
}

/** Surface text of the selection; separated parts are joined with "…" ("turned … off"). */
export function selectionText(tokens: Token[], indices: number[]): string {
  const sorted = [...indices].sort((a, b) => a - b);
  let out = "";
  sorted.forEach((i, n) => {
    if (n > 0) out += sorted[n - 1] + 1 === i ? tokens[sorted[n - 1]].ws : " … ";
    out += tokens[i].t;
  });
  return out;
}

export function sentenceText(tokens: Token[], s: number): string {
  return tokens
    .filter((t) => t.s === s)
    .map((t) => t.t + t.ws)
    .join("")
    .trim();
}

export function statusClass(term: Term | undefined): string {
  if (!term) return "st-new";
  if (term.status >= 1 && term.status <= 4) return `st-${term.status}`;
  return "";
}

const span = (u: { i: number[] }) => u.i[u.i.length - 1] - u.i[0];

/** Token index → indices of the units it belongs to, widest first: an expression, then the
 * phrasal verb inside it. Clicking the same word again steps through them, then the word. */
export function unitsByToken(section: Section): Map<number, number[]> {
  const map = new Map<number, number[]>();
  const order = section.units.map((u, n) => ({ u, n })).sort((a, b) => span(b.u) - span(a.u));
  for (const { u, n } of order) {
    for (const i of u.i) map.set(i, [...(map.get(i) ?? []), n]);
  }
  return map;
}

export function sameSelection(a: Selection | null, b: Selection): boolean {
  return !!a && a.kind === b.kind && a.key === b.key && a.tokens.join() === b.tokens.join();
}
