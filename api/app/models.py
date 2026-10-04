from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# Term status. Words with no Term row are "new" (blue in the reader).
IGNORED = -1
LEARNING = (1, 2, 3, 4)  # New, Recognized, Familiar, Learned
KNOWN = 5

# phrase: a selection the reader saved; expression: an idiom or set phrase the parser found.
KINDS = ("word", "phrase", "phrasal_verb", "expression")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    language: Mapped[str] = mapped_column(String(10))
    current_position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sections: Mapped[list["Section"]] = relationship(
        back_populates="book", cascade="all, delete-orphan", order_by="Section.position"
    )


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    text: Mapped[str] = mapped_column(Text)
    # Tokenized once on import so the reader never runs the NLP pipeline.
    tokens: Mapped[list] = mapped_column(JSON)
    units: Mapped[list] = mapped_column(JSON)
    grammar: Mapped[list] = mapped_column(JSON, default=list)
    word_count: Mapped[int] = mapped_column(Integer)

    book: Mapped[Book] = relationship(back_populates="sections")


class Term(Base):
    __tablename__ = "terms"
    __table_args__ = (UniqueConstraint("language", "key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    language: Mapped[str] = mapped_column(String(10), index=True)
    key: Mapped[str] = mapped_column(String(300))
    kind: Mapped[str] = mapped_column(String(20), default="word")
    status: Mapped[int] = mapped_column(Integer, default=1)
    meaning: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    context: Mapped[str] = mapped_column(Text, default="")
    srs_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    srs_step: Mapped[int] = mapped_column(Integer, default=0)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DictionaryCache(Base):
    """Remote dictionary responses, so each term is fetched once."""

    __tablename__ = "dictionary_cache"

    key: Mapped[str] = mapped_column(String(400), primary_key=True)
    entries: Mapped[list] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AudioCache(Base):
    """Pronunciation recordings fetched from Wikimedia Commons, kept so each is downloaded once."""

    __tablename__ = "audio_cache"

    url: Mapped[str] = mapped_column(String(600), primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    content_type: Mapped[str] = mapped_column(String(100))


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
