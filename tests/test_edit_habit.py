"""Tests for editing habits: rename, goal/category updates, shared visibility.

Runs on a temporary database so the real ``habits.db`` is never touched.
"""

import os
import tempfile

import db
from db import (init_db, save_habit, load_habits, add_member,
                create_user, get_user_by_username)
from habits.habit import Habit

_ORIGINAL_DB = db.DB_NAME
_TMP_DB = None


def setup_module(module):
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


def test_rename_updates_in_place_without_duplicating():
    anna = get_user_by_username("anna")
    habit = Habit(name="Old name", periodicity="daily")
    save_habit(habit, anna.user_id)
    original_id = habit.habit_id

    habit.name = "New name"
    save_habit(habit, anna.user_id)

    habits = load_habits(anna.user_id)
    names = [h.name for h in habits]
    assert "New name" in names
    assert "Old name" not in names          # nessun duplicato fantasma
    renamed = next(h for h in habits if h.name == "New name")
    assert renamed.habit_id == original_id  # stessa habit, stesso id


def test_edit_goal_and_category_persist():
    anna = get_user_by_username("anna")
    habit = Habit(name="Tweak me", periodicity="weekly", category="Work", goal=1)
    save_habit(habit, anna.user_id)

    habit.goal = 3
    habit.category = "Fitness"
    save_habit(habit, anna.user_id)

    loaded = next(h for h in load_habits(anna.user_id) if h.name == "Tweak me")
    assert loaded.goal == 3
    assert loaded.category == "Fitness"


def test_rename_of_shared_habit_visible_to_all_members():
    anna = get_user_by_username("anna")
    marco = get_user_by_username("marco")
    habit = Habit(name="Chores", periodicity="weekly")
    save_habit(habit, anna.user_id)
    add_member(habit.habit_id, marco.user_id)

    habit.name = "House chores"
    save_habit(habit, anna.user_id)

    marco_names = [h.name for h in load_habits(marco.user_id)]
    assert "House chores" in marco_names
    assert "Chores" not in marco_names
