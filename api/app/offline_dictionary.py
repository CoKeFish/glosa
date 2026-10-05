"""The whole Wiktionary, downloaded once, so looking a word up needs no internet.

Kaikki publishes each edition as one JSON line per entry. The import streams the dump,
keeps only the fields glosa reads (see kaikki.parse_lines and parse_native_lines) and the
translations into the meaning languages glosa offers, and stores the lines per word. A
lookup then reads the stored lines instead of fetching kaikki.org.
"""

import json
import zlib

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from app.db import SessionLocal
from app.models import OfflineEntry

MEANING_LANGUAGES = {"es", "fr", "pt", "it"}
# (source key, url, approximate compressed size in bytes); the English edition first.
DUMPS = [
    ("en", "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl.gz", 523_000_000),
    ("native-es", "https://kaikki.org/eswiktionary/Ingl%C3%A9s/kaikki.org-dictionary-Ingl%C3%A9s.jsonl.gz", 5_000_000),
]
USER_AGENT = "glosa/0.1 (https://github.com/CoKeFish/glosa)"
BATCH = 2000


def reduce_line(d: dict) -> dict:
    """Only what glosa reads from an entry: a fraction of the dump's size."""
    senses = []
    for s in d.get("senses", []):
        sense = {k: s[k] for k in ("glosses", "tags", "form_of", "alt_of") if s.get(k)}
        if s.get("links"):
            sense["links"] = s["links"][:1]
        examples = [{"text": e["text"]} for e in s.get("examples", [])[:1] if e.get("text")]
        if examples:
            sense["examples"] = examples
        senses.append(sense)
    out = {"word": d.get("word", ""), "pos": d.get("pos", ""), "senses": senses}
    for key in ("pos_title", "etymology_number"):
        if d.get(key):
            out[key] = d[key]
    translations = [
        {k: t[k] for k in ("lang_code", "word", "sense") if t.get(k)}
        for t in d.get("translations", []) if t.get("lang_code") in MEANING_LANGUAGES and t.get("word")
    ]
    if translations:
        out["translations"] = translations
    if d.get("forms"):
        out["forms"] = [{k: f[k] for k in ("form", "tags") if f.get(k)} for f in d["forms"][:40]]
    sounds = [{k: s[k] for k in ("ipa", "mp3_url", "ogg_url", "tags") if s.get(k)} for s in d.get("sounds", [])]
    sounds = [s for s in sounds if s.get("ipa") or s.get("mp3_url") or s.get("ogg_url")]
    if sounds:
        out["sounds"] = sounds[:6]
    return out


def lines(source: str, word: str) -> list[dict] | None:
    """Stored entries for a word, or None when the offline dictionary does not have it."""
    try:
        with SessionLocal() as session:
            row = session.get(OfflineEntry, (source, word))
            return row.lines if row else None
    except Exception:  # SQLite in tests, or the table not created yet
        return None


def ready() -> bool:
    try:
        with SessionLocal() as session:
            return (session.scalar(select(func.count()).select_from(OfflineEntry).where(OfflineEntry.source == "en")) or 0) > 0
    except Exception:
        return False


def _flush(session, source: str, buffer: dict[str, list[dict]]) -> None:
    if not buffer:
        return
    stmt = insert(OfflineEntry).values([{"source": source, "word": w, "lines": ls} for w, ls in buffer.items()])
    # The same word can come back later in the dump: append, never overwrite.
    stmt = stmt.on_conflict_do_update(
        index_elements=["source", "word"],
        set_={"lines": OfflineEntry.lines.op("||")(stmt.excluded.lines)},
    )
    session.execute(stmt)
    session.commit()
    buffer.clear()


def install(report) -> None:
    total = sum(size for _, _, size in DUMPS)
    done_before = 0
    uninstall()  # a clean import, never half of two
    with SessionLocal() as session:
        for source, url, size in DUMPS:
            decompress = zlib.decompressobj(16 + zlib.MAX_WBITS)
            pending, buffer, read = b"", {}, 0
            with httpx.stream("GET", url, headers={"User-Agent": USER_AGENT}, timeout=None,
                              follow_redirects=True) as resp:
                if resp.status_code != 200:
                    raise RuntimeError(f"kaikki.org respondió {resp.status_code}")
                for chunk in resp.iter_bytes(1 << 20):
                    read += len(chunk)
                    pending += decompress.decompress(chunk)
                    *complete, pending = pending.split(b"\n")
                    for raw in complete:
                        if not raw.strip():
                            continue
                        d = json.loads(raw)
                        if d.get("lang_code", "en") != "en" or not d.get("word"):
                            continue
                        buffer.setdefault(d["word"], []).append(reduce_line(d))
                    if len(buffer) >= BATCH:
                        _flush(session, source, buffer)
                    report(min(0.99, (done_before + read) / total), "importing")
            pending += decompress.flush()
            for raw in pending.split(b"\n"):
                if raw.strip():
                    d = json.loads(raw)
                    if d.get("lang_code", "en") == "en" and d.get("word"):
                        buffer.setdefault(d["word"], []).append(reduce_line(d))
            _flush(session, source, buffer)
            done_before += size


def uninstall() -> None:
    with SessionLocal() as session:
        session.execute(delete(OfflineEntry))
        session.commit()
