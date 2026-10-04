"""Turn uploaded files into book sections of readable length."""

import io
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

MAX_WORDS_PER_SECTION = 2000
BLOCK_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "pre"]


class ImportError_(Exception):
    pass


@dataclass
class RawSection:
    title: str
    text: str


def _word_count(text: str) -> int:
    return len(text.split())


def split_long(title: str, text: str, max_words: int = MAX_WORDS_PER_SECTION) -> list[RawSection]:
    """Split on paragraph boundaries so no section is much longer than max_words."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, current, count = [], [], 0
    for p in paragraphs:
        words = _word_count(p)
        if current and count + words > max_words:
            chunks.append(current)
            current, count = [], 0
        current.append(p)
        count += words
    if current:
        chunks.append(current)
    if len(chunks) <= 1:
        return [RawSection(title, "\n\n".join(chunks[0]))] if chunks else []
    return [RawSection(f"{title} ({n}/{len(chunks)})", "\n\n".join(c)) for n, c in enumerate(chunks, 1)]


def from_text(title: str, text: str) -> list[RawSection]:
    text = text.replace("\r\n", "\n").strip()
    if not text:
        raise ImportError_("El texto está vacío")
    return split_long(title, text)


def _html_to_text(html: bytes | str) -> tuple[str | None, str]:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find(["h1", "h2", "h3"])
    blocks = [" ".join(el.get_text(" ").split()) for el in soup.find_all(BLOCK_TAGS)]
    blocks = [b for b in blocks if b]
    if not blocks:
        body = soup.body or soup
        blocks = [line.strip() for line in body.get_text("\n").splitlines() if line.strip()]
    title = " ".join(heading.get_text(" ").split()) if heading else None
    return title, "\n\n".join(blocks)


def from_epub(data: bytes) -> tuple[str | None, list[RawSection]]:
    from ebooklib import ITEM_DOCUMENT, epub

    try:
        book = epub.read_epub(io.BytesIO(data), options={"ignore_ncx": True})
    except Exception as exc:  # ebooklib raises bare exceptions for malformed files
        raise ImportError_(f"No se pudo leer el EPUB: {exc}") from exc

    meta_title = book.get_metadata("DC", "title")
    book_title = meta_title[0][0] if meta_title else None
    sections: list[RawSection] = []
    for idref, _linear in book.spine:
        item = book.get_item_with_id(idref)
        if item is None or item.get_type() != ITEM_DOCUMENT:
            continue
        heading, text = _html_to_text(item.get_content())
        if _word_count(text) < 5:
            continue  # covers, blank pages
        sections.extend(split_long(heading or f"Sección {len(sections) + 1}", text))
    if not sections:
        raise ImportError_("El EPUB no tiene texto legible")
    return book_title, sections


def from_upload(filename: str, data: bytes) -> tuple[str | None, list[RawSection]]:
    name = filename.lower()
    stem = filename.rsplit(".", 1)[0]
    if name.endswith(".epub"):
        return from_epub(data)
    if name.endswith((".txt", ".md")):
        return stem, from_text(stem, data.decode("utf-8", errors="replace"))
    if name.endswith((".html", ".htm")):
        title, text = _html_to_text(data)
        return title or stem, from_text(title or stem, text)
    raise ImportError_("Formato no soportado todavía. Usa EPUB, TXT o HTML.")
