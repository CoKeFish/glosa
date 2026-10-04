import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { api, IGNORED, KNOWN, Section, Term } from "../api";
import { TermPanel } from "../components/TermPanel";
import { Cover } from "../Cover";
import { useI18n } from "../i18n";
import { Cards, ChevronLeft, ChevronRight, Close, Gear } from "../icons";
import { sameSelection, Selection, statusClass, unitsByToken, wordSelection } from "../reading";

type Undo = { language: string; keys: string[] };

const SHORTCUTS = [
  ["Click", "key.click"],
  ["Alt + click", "key.altClick"],
  ["Drag", "key.drag"],
  ["Double click", "key.sentence"],
  ["1 – 4", "key.status"],
  ["K", "key.known"],
  ["X", "key.ignore"],
  ["H", "key.meaning"],
  ["S", "key.listen"],
  ["A", "key.listenSentence"],
  ["← →", "key.move"],
  ["B", "key.nextNew"],
  ["Esc", "key.close"],
] as const;

export function Reader() {
  const { t } = useI18n();
  const { sectionId } = useParams();
  const navigate = useNavigate();
  const [section, setSection] = useState<Section | null>(null);
  const [terms, setTerms] = useState<Record<string, Term>>({});
  const [selection, setSelection] = useState<Selection | null>(null);
  const [hoverUnit, setHoverUnit] = useState<number | null>(null);
  const [activeGrammar, setActiveGrammar] = useState<number | null>(null);
  const [pageMarksKnown, setPageMarksKnown] = useState(true);
  const [clickSaves, setClickSaves] = useState(true);
  const [autoPlay, setAutoPlay] = useState(true);
  const [undo, setUndo] = useState<Undo | null>(null);
  const [notice, setNotice] = useState("");
  const [help, setHelp] = useState(false);
  const dragStart = useRef<number | null>(null);
  const [dragRange, setDragRange] = useState<[number, number] | null>(null);

  const load = useCallback(async (keepSelection = false) => {
    const s = await api.section(Number(sectionId));
    setSection(s);
    setTerms(s.terms);
    if (!keepSelection) {
      setSelection(null);
      setActiveGrammar(null);
    }
    api.setPosition(s.book.id, s.position).catch(() => {});
  }, [sectionId]);

  useEffect(() => {
    load();
    window.scrollTo(0, 0);
  }, [load]);

  useEffect(() => {
    api
      .settings()
      .then((s) => {
        setPageMarksKnown(s.reader.page_marks_known);
        setClickSaves(s.reader.click_saves);
        setAutoPlay(s.reader.auto_play);
      })
      .catch(() => {});
  }, []);

  const byToken = useMemo(() => (section ? unitsByToken(section) : new Map<number, number[]>()), [section]);

  const select = useCallback(
    (i: number, wordOnly = false, clicked = false) => {
      if (!section) return;
      const base = wordSelection(section.tokens, i);
      if (!base) return;
      const word = { ...base, clicked };
      const units = wordOnly ? [] : (byToken.get(i) ?? []).filter((n) => terms[section.units[n].k]?.status !== IGNORED);
      // Layers under this word, widest first, ending with the word itself.
      const layers: Selection[] = [
        ...units.map((n) => {
          const u = section.units[n];
          return { kind: u.kind, key: u.k, tokens: u.i, sub: u.sub, word, clicked } as Selection;
        }),
        word,
      ];
      // Clicking the same word again moves one layer in; after the word it starts over.
      setSelection((prev) => {
        const at = layers.findIndex((l) => sameSelection(prev, l));
        return layers[at >= 0 ? (at + 1) % layers.length : 0];
      });
    },
    [section, byToken, terms],
  );

  function selectRange(a: number, b: number) {
    if (!section) return;
    let [lo, hi] = a < b ? [a, b] : [b, a];
    // Trim leading/trailing punctuation and whitespace tokens.
    while (lo < hi && !section.tokens[lo].w) lo++;
    while (hi > lo && !section.tokens[hi].w && !/[.!?…"”')]/.test(section.tokens[hi].t)) hi--;
    const range = Array.from({ length: hi - lo + 1 }, (_, n) => lo + n);
    const words = range.filter((i) => section.tokens[i].w);
    if (words.length < 2) return select(words[0] ?? a);
    window.getSelection()?.removeAllRanges();
    // Selecting exactly the words of a marked unit ("led to" → saved "lead to") opens that
    // unit, with its saved meaning and status, instead of creating a duplicate phrase.
    const unit = section.units.find(
      (u) => u.kind !== "phrase" && u.i.filter((i) => section.tokens[i].w).join() === words.join(),
    );
    if (unit) {
      setSelection({ kind: unit.kind, key: unit.k, tokens: unit.i, sub: unit.sub });
      return;
    }
    setSelection({ kind: "phrase", key: words.map((i) => section.tokens[i].k).join(" "), tokens: range });
  }

  function selectSentence(i: number) {
    if (!section) return;
    const s = section.tokens[i].s;
    const indices = section.tokens.map((tok, n) => (tok.s === s ? n : -1)).filter((n) => n >= 0);
    selectRange(indices[0], indices[indices.length - 1]);
  }

  function onSaved(term: Term) {
    setTerms((prev) => ({ ...prev, [term.key]: term }));
    // A new phrase or expression must show up as a unit wherever it occurs on the page.
    if ((term.kind === "phrase" || term.kind === "expression") && !section?.units.some((u) => u.k === term.key)) {
      load(true);
    }
  }

  function onRemoved(term: Term) {
    setTerms((prev) => {
      const next = { ...prev };
      delete next[term.key];
      return next;
    });
    // A removed phrase or expression the parser did not find must stop being marked.
    if (term.kind === "phrase" || term.kind === "expression") {
      load(true);
      if (term.kind === "phrase") setSelection(null);
    }
  }

  async function turnPage(target: number | null) {
    if (!section) return;
    if (pageMarksKnown) {
      const keys = [...new Set(section.tokens.filter((t) => t.w && t.k && !terms[t.k]).map((t) => t.k!))];
      if (keys.length) {
        const { created } = await api.markKnown(section.book.language, keys);
        setUndo(created.length ? { language: section.book.language, keys: created } : null);
      }
    }
    navigate(target ? `/read/${target}` : `/books/${section.book.id}`);
  }

  async function undoKnown() {
    if (!undo) return;
    await api.undoKnown(undo.language, undo.keys);
    setUndo(null);
    load();
  }

  // Navigation shortcuts. Status shortcuts live in the term panel.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) || !section) return;
      const current = selection?.tokens[0] ?? -1;
      const step = (dir: 1 | -1, pred: (i: number) => boolean) => {
        for (let i = current + dir; i >= 0 && i < section.tokens.length; i += dir) if (pred(i)) return select(i);
      };
      if (e.key === "ArrowRight") step(1, (i) => section.tokens[i].w);
      else if (e.key === "ArrowLeft") step(-1, (i) => section.tokens[i].w);
      else if (e.key === "b") step(1, (i) => section.tokens[i].w && !terms[section.tokens[i].k!]);
      else if (e.key === "Escape") setSelection(null);
      else return;
      e.preventDefault();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [section, selection, terms, select]);

  if (!section) return <div className="page muted">{t("loading")}</div>;

  // Live range while dragging, or the selected phrase/sentence once released.
  const range: [number, number] | null =
    dragRange && dragRange[0] !== dragRange[1]
      ? dragRange
      : selection?.kind === "phrase"
        ? [selection.tokens[0], selection.tokens[selection.tokens.length - 1]]
        : null;
  const selected = new Set(selection?.kind === "phrase" ? [] : selection?.tokens ?? []);
  const hovered = new Set(hoverUnit !== null ? section.units[hoverUnit].i : []);
  const grammarTokens = new Set(activeGrammar !== null ? section.grammar[activeGrammar].i : []);
  const progress = section.book.sections > 1 ? section.position / (section.book.sections - 1) : 1;
  const newWords = new Set(section.tokens.filter((t) => t.w && !terms[t.k!]).map((t) => t.k)).size;
  const learning = Object.values(terms).filter((t) => t.status >= 1 && t.status <= 4).length;

  return (
    <div className="reader-shell">
      <header className="reader-top">
        <Link to={`/books/${section.book.id}`} className="icon-btn" aria-label={t("reader.close")} style={{ justifySelf: "start" }}>
          <Close />
        </Link>
        <div className="progress" title={`${section.position + 1} / ${section.book.sections}`}>
          <div className="fill" style={{ width: `${progress * 100}%` }} />
          <div className="knob" style={{ left: `${progress * 100}%` }} />
        </div>
        <div className="right">
          <Link to="/settings" className="icon-btn" aria-label={t("nav.settings")} title={t("nav.settings")}>
            <Gear />
          </Link>
        </div>
      </header>

      <div className="reader-body">
        <button
          className="icon-btn page-arrow"
          aria-label={t("reader.prev")}
          disabled={!section.prev_id}
          onClick={() => section.prev_id && navigate(`/read/${section.prev_id}`)}
        >
          <ChevronLeft size={40} />
        </button>

        <div>
          <div className="lesson-head">
            <Cover title={section.book.title} size="sm" />
            <div>
              <div className="crumb">{section.book.title} · {section.position + 1}/{section.book.sections}</div>
              <h1>{section.title}</h1>
            </div>
          </div>
          {undo && (
            <div className="toast">
              {t("reader.markedKnown", { n: undo.keys.length })}
              <button onClick={undoKnown}>{t("reader.undo")}</button>
            </div>
          )}
          {notice && (
            <div className="toast" onClick={() => setNotice("")}>{notice}</div>
          )}

          <div
            className={`text ${dragRange ? "dragging" : ""}`}
            onMouseLeave={() => {
              dragStart.current = null;
              setDragRange(null);
            }}
            onMouseUp={() => {
              // Released over whitespace: finish the drag with the last word reached.
              if (dragStart.current !== null && dragRange) selectRange(dragRange[0], dragRange[1]);
              dragStart.current = null;
              setDragRange(null);
            }}
          >
            {section.tokens.map((tok, i) => {
              const inRange = range !== null && i >= range[0] && i <= range[1];
              const rangeClass = inRange ? (dragRange ? "rng dragging" : "rng") : "";
              const wsClass = inRange && i < range![1] ? rangeClass : "";
              if (!tok.w) {
                return (
                  <span key={i}>
                    <span className={rangeClass}>{tok.t}</span>
                    <span className={wsClass}>{tok.ws}</span>
                  </span>
                );
              }
              const classes = ["tok", statusClass(terms[tok.k!]), rangeClass];
              for (const n of byToken.get(i) ?? []) {
                const unit = section.units[n];
                const unitTerm = terms[unit.k];
                if (unitTerm?.status === IGNORED) continue;
                classes.push(unit.kind === "phrasal_verb" ? "pv" : unit.kind === "expression" ? "ex" : "ph");
                if (unitTerm) classes.push(unitTerm.status === KNOWN ? "u-known" : "u-saved");
                break;
              }
              if (selected.has(i)) classes.push("sel");
              if (hovered.has(i)) classes.push("hover");
              if (grammarTokens.has(i)) classes.push("gram");
              return (
                <span key={i}>
                  <span
                    className={classes.join(" ")}
                    onMouseDown={(e) => {
                      if (e.button !== 0) return;
                      e.preventDefault();
                      dragStart.current = i;
                      setDragRange([i, i]);
                    }}
                    onMouseUp={(e) => {
                      e.stopPropagation();
                      const start = dragStart.current;
                      dragStart.current = null;
                      setDragRange(null);
                      if (e.detail === 2) selectSentence(i);
                      else if (start !== null && start !== i) selectRange(start, i);
                      else select(i, e.altKey, true);
                    }}
                    onMouseEnter={() => {
                      setHoverUnit(byToken.get(i)?.[0] ?? null);
                      if (dragStart.current !== null) {
                        const s = dragStart.current;
                        setDragRange(s < i ? [s, i] : [i, s]);
                      }
                    }}
                    onMouseLeave={() => setHoverUnit(null)}
                  >
                    {tok.t}
                  </span>
                  <span className={wsClass}>{tok.ws}</span>
                </span>
              );
            })}
          </div>

          <div className="end-of-page">
            <button onClick={() => turnPage(section.next_id)}>
              {section.next_id ? t("reader.nextLesson") : t("reader.finish")}
            </button>
          </div>
        </div>

        <button className="icon-btn page-arrow" aria-label={t("reader.next")} onClick={() => turnPage(section.next_id)}>
          <ChevronRight size={40} />
        </button>

        <aside className="side">
          {selection ? (
            <TermPanel
              key={selection.key + selection.tokens.join(",")}
              section={section}
              selection={selection}
              term={terms[selection.key]}
              onSaved={onSaved}
              onRemoved={onRemoved}
              onSelect={setSelection}
              autoSave={clickSaves && !!selection.clicked && selection.kind !== "phrase"}
              autoPlay={autoPlay}
              onClose={() => setSelection(null)}
              activeGrammar={activeGrammar}
              onGrammar={setActiveGrammar}
            />
          ) : (
            <div className="side-empty">
              <strong>{t("reader.emptyTitle")}</strong> {t("reader.emptyBody")}
              <div className="legend">
                <span><span className="tok st-new">{t("reader.legendBlue")}</span> {t("reader.legendNew")}</span>
                <span><span className="tok st-1">{t("reader.legendYellow")}</span> {t("reader.legendLingq")}</span>
                <span><span className="tok pv">{t("reader.legendUnderline")}</span> {t("reader.legendPhrasal")}</span>
                <span><span className="tok ex">{t("reader.legendUnderline")}</span> {t("reader.legendExpression")}</span>
              </div>
            </div>
          )}
        </aside>
      </div>

      <footer className="reader-bottom">
        <span />
        <div className="center">
          <span><strong>{newWords}</strong> {t("reader.newWords")}</span>
          <span><strong>{learning}</strong> {t("reader.learning")}</span>
        </div>
        <div className="right">
          <Link to="/review" className="review-link" title={t("reader.review")}><Cards /> {learning}</Link>
          <button className="help-fab" aria-label={t("reader.shortcuts")} onClick={() => setHelp((h) => !h)}>?</button>
        </div>
      </footer>
      {help && (
        <div className="help-pop" onClick={() => setHelp(false)}>
          <dl>
            {SHORTCUTS.map(([k, v]) => (
              <Fragment key={k}><dt><kbd>{k}</kbd></dt><dd style={{ margin: 0 }}>{t(v)}</dd></Fragment>
            ))}
          </dl>
        </div>
      )}
    </div>
  );
}
