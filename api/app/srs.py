"""Spaced repetition, following LingQ's published intervals.

Status 1 → 1 day, 2 → 3 days, 3 → 1 week, 4 → 2 weeks, then 1 month, then 3 months.
Two correct answers in a row raise the status by one.
"""

from datetime import datetime, timedelta

from app.models import LEARNING, Term

INTERVAL_DAYS = {1: 1, 2: 3, 3: 7}
STATUS_4_STEPS = [14, 30, 90]
CORRECT_TO_ADVANCE = 2


def next_due(status: int, step: int, now: datetime) -> datetime | None:
    if status not in LEARNING:
        return None  # Known and ignored terms are never reviewed.
    if status == 4:
        days = STATUS_4_STEPS[min(step, len(STATUS_4_STEPS) - 1)]
    else:
        days = INTERVAL_DAYS[status]
    return now + timedelta(days=days)


def set_status(term: Term, status: int, now: datetime) -> None:
    """Manual status change from the reader or the vocabulary list."""
    if status != term.status:
        term.srs_step = 0
    term.status = status
    term.streak = 0
    term.srs_due = next_due(status, term.srs_step, now)


def answer(term: Term, correct: bool, now: datetime) -> None:
    """Record a review answer. A term stays due until it is answered right twice in a row."""
    if not correct:
        term.streak = 0
        return
    term.streak += 1
    if term.streak < CORRECT_TO_ADVANCE:
        return
    term.streak = 0
    if term.status < 4:
        term.status += 1
        term.srs_step = 0
    else:
        term.srs_step += 1
    term.srs_due = next_due(term.status, term.srs_step, now)
