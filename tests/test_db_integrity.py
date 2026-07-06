"""Integration tests for the SQLite persistence layer.

All tests run against a temporary database file so the real ``habits.db``
is never touched.
"""

import os
import tempfile
from datetime import datetime

import db
from db import (init_db, save_habit, load_habits, delete_habit,
                create_user, get_user_by_username)
from habits.habit import Habit

_ORIGINAL_DB = db.DB_NAME
_TMP_DB = None


def setup_module(module):
    """Point the db module at a fresh temporary database."""
    global _TMP_DB
    fd, _TMP_DB = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(_TMP_DB)
    db.DB_NAME = _TMP_DB
    init_db()
    create_user("tester", "tester@example.com")


def teardown_module(module):
    """Restore the original database name and delete the temp file."""
    db.DB_NAME = _ORIGINAL_DB
    if _TMP_DB and os.path.exists(_TMP_DB):
        os.remove(_TMP_DB)


def _user():
    return get_user_by_username("tester")


def test_save_and_load_habit_roundtrip():
    user = _user()
    habit = Habit(name="Test DB", periodicity="weekly", category="Work",
                  goal=2, completions=[datetime(2026, 7, 1, 9, 30)])
    save_habit(habit, user.user_id)

    loaded = load_habits(user.user_id)
    match = next(h for h in loaded if h.name == "Test DB")
    assert match.periodicity == "weekly"
    assert match.goal == 2
    assert match.completions == [datetime(2026, 7, 1, 9, 30)]
    # Fixture records without an author are attributed to the saving user
    assert match.records[0]["user_id"] == user.user_id
    assert match.user_id == user.user_id
    assert match.habit_id is not None


def test_save_existing_habit_updates_instead_of_duplicating():
    user = _user()
    habit = Habit(name="Upsert me", periodicity="daily")
    save_habit(habit, user.user_id)
    habit.complete()
    save_habit(habit, user.user_id)

    loaded = [h for h in load_habits(user.user_id) if h.name == "Upsert me"]
    assert len(loaded) == 1
    assert loaded[0].progress == 1


def test_delete_habit_removes_row():
    user = _user()
    habit = Habit(name="Delete me", periodicity="daily")
    save_habit(habit, user.user_id)
    delete_habit(habit.habit_id)
    names = [h.name for h in load_habits(user.user_id)]
    assert "Delete me" not in names
