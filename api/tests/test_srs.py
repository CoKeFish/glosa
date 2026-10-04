from datetime import datetime, timedelta, timezone

from app import srs
from app.models import KNOWN, Term

NOW = datetime(2026, 10, 4, tzinfo=timezone.utc)


def new_term(status=1):
    t = Term(key="x", language="en", status=status, srs_step=0, streak=0)
    srs.set_status(t, status, NOW)
    return t


def test_intervals_follow_status():
    assert new_term(1).srs_due == NOW + timedelta(days=1)
    assert new_term(3).srs_due == NOW + timedelta(days=7)
    assert new_term(KNOWN).srs_due is None


def test_two_correct_answers_advance_status():
    t = new_term(1)
    srs.answer(t, True, NOW)
    assert t.status == 1
    srs.answer(t, True, NOW)
    assert t.status == 2
    assert t.srs_due == NOW + timedelta(days=3)


def test_wrong_answer_resets_streak():
    t = new_term(2)
    srs.answer(t, True, NOW)
    srs.answer(t, False, NOW)
    srs.answer(t, True, NOW)
    assert t.status == 2


def test_status_4_climbs_through_steps():
    t = new_term(4)
    assert t.srs_due == NOW + timedelta(days=14)
    for _ in range(2):
        srs.answer(t, True, NOW)
    assert t.srs_due == NOW + timedelta(days=30)
    for _ in range(4):
        srs.answer(t, True, NOW)
    assert t.srs_due == NOW + timedelta(days=90)
