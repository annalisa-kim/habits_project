"""Tests for the shared-habit feature (membership, completions, analytics).

Runs on a temporary database so the real ``habits.db`` is never touched.
"""

import os
import tempfile
from datetime import datetime, timedelta

import db
from db import (init_db, save_habit, load_habits, add_member, remove_member,
                get_members, create_user, get_user_by_username)
from habits.habit import Habit
from analytics.progress import calculate_streak, get_member_contributions

_ORIGINAL_DB = db.DB_NAME
_TMP_DB = None
NOW = datetime(2026, 7, 6, 12, 0)


def setup_module(module):
    """Point the db module at a fresh temporary database with two users."""
    global _TMP_DB
    fd, _TMP_DB = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(_TMP_DB)
    db.DB_NAME = _TMP_DB
    init_db()
    create_user("anna")
    create_user("marco")


def teardown_module(module):
    db.DB_NAME = _ORIGINAL_DB
    if _TMP_DB and os.path.exists(_TMP_DB):
        os.remove(_TMP_DB)


def _users():
    return get_user_by_username("anna"), get_user_by_username("marco")


def _fresh_habit(name):
    anna, _ = _users()
    habit = Habit(name=name, periodicity="daily")
    save_habit(habit, anna.user_id)
    return habit


def test_creator_is_first_member():
    anna, _ = _users()
    habit = _fresh_habit("Solo habit")
    members = get_members(habit.habit_id)
    assert members == [(anna.user_id, "anna")]

    loaded = next(h for h in load_habits(anna.user_id) if h.name == "Solo habit")
    assert loaded.shared is False


def test_shared_habit_visible_to_both_members():
    anna, marco = _users()
    habit = _fresh_habit("Clean bathroom")
    add_member(habit.habit_id, marco.user_id)

    for user in (anna, marco):
        names = [h.name for h in load_habits(user.user_id)]
        assert "Clean bathroom" in names

    loaded = next(h for h in load_habits(marco.user_id)
                  if h.name == "Clean bathroom")
    assert loaded.shared is True
    assert sorted(loaded.member_names) == ["anna", "marco"]


def test_add_member_is_idempotent():
    _, marco = _users()
    habit = _fresh_habit("Idempotent")
    add_member(habit.habit_id, marco.user_id)
    add_member(habit.habit_id, marco.user_id)
    assert len(get_members(habit.habit_id)) == 2


def test_completion_records_who_completed():
    anna, marco = _users()
    habit = _fresh_habit("Dishes")
    add_member(habit.habit_id, marco.user_id)

    habit.complete(user_id=marco.user_id, when=NOW)
    save_habit(habit, anna.user_id)

    loaded = next(h for h in load_habits(anna.user_id) if h.name == "Dishes")
    assert loaded.records[-1]["user_id"] == marco.user_id
    assert loaded.records[-1]["timestamp"] == NOW


def test_group_streak_counts_completions_from_any_member():
    anna, marco = _users()
    habit = Habit(name="Group streak", periodicity="daily")
    # Alternating members over 4 consecutive days → group streak of 4
    for day, uid in enumerate([anna.user_id, marco.user_id,
                               anna.user_id, marco.user_id]):
        habit.complete(user_id=uid, when=NOW - timedelta(days=day))
    assert calculate_streak(habit) == 4


def test_member_contributions_counts_per_user():
    anna, marco = _users()
    habit = Habit(name="Contribs", periodicity="daily")
    habit.complete(user_id=anna.user_id, when=NOW)
    habit.complete(user_id=marco.user_id, when=NOW - timedelta(days=1))
    habit.complete(user_id=marco.user_id, when=NOW - timedelta(days=2))

    contributions = get_member_contributions(habit)
    assert contributions[0] == (marco.user_id, 2)
    assert contributions[1] == (anna.user_id, 1)


def test_member_contributions_respects_since():
    anna, marco = _users()
    habit = Habit(name="Since", periodicity="daily")
    habit.complete(user_id=anna.user_id, when=NOW - timedelta(days=40))
    habit.complete(user_id=marco.user_id, when=NOW)

    recent = dict(get_member_contributions(habit,
                                           since=NOW - timedelta(days=7)))
    assert recent == {marco.user_id: 1}


def test_remove_member_deletes_only_for_that_user():
    anna, marco = _users()
    habit = _fresh_habit("Leave me")
    add_member(habit.habit_id, marco.user_id)

    remove_member(habit.habit_id, marco.user_id)
    assert "Leave me" not in [h.name for h in load_habits(marco.user_id)]
    assert "Leave me" in [h.name for h in load_habits(anna.user_id)]


def test_last_member_leaving_deletes_the_habit():
    anna, _ = _users()
    habit = _fresh_habit("Ghost habit")
    remove_member(habit.habit_id, anna.user_id)
    assert "Ghost habit" not in [h.name for h in load_habits()]
