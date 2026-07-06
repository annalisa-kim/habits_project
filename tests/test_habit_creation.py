"""Unit tests for creating Habit objects and (de)serializing them."""

from datetime import datetime

from habits.habit import Habit


def test_create_habit_instance():
    habit = Habit(name="Drink Water", periodicity="daily",
                  category="Health", goal=8)
    assert habit.name == "Drink Water"
    assert habit.periodicity == "daily"
    assert habit.category == "Health"
    assert habit.goal == 8
    assert habit.progress == 0
    assert habit.completions == []
    assert habit.created_at is not None


def test_to_dict_from_dict_roundtrip():
    habit = Habit(name="Read", periodicity="weekly", category="Study",
                  goal=1, completions=[datetime(2026, 6, 1, 8, 0)])
    clone = Habit.from_dict(habit.to_dict())
    assert clone.name == habit.name
    assert clone.periodicity == habit.periodicity
    assert clone.completions == habit.completions
    assert clone.start_date == habit.start_date
