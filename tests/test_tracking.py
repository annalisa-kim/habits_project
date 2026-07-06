"""Unit tests for checking off habits (tracking)."""

from datetime import datetime, timedelta

from habits.habit import Habit


def test_complete_records_timestamp_and_progress():
    habit = Habit(name="Read", periodicity="daily", category="Study", goal=2)
    habit.complete()
    assert habit.progress == 1
    assert len(habit.completions) == 1
    assert isinstance(habit.completions[0], datetime)


def test_completed_today_is_computed_from_completions():
    habit = Habit(name="Read", periodicity="daily")
    assert habit.completed_today is False
    habit.complete()  # now
    assert habit.completed_today is True

    stale = Habit(name="Old", periodicity="daily",
                  completions=[datetime.now() - timedelta(days=2)])
    assert stale.completed_today is False


def test_mood_can_be_recorded():
    habit = Habit(name="Read", periodicity="daily", goal=1)
    habit.mood[datetime.now().isoformat()] = "🙂"
    assert len(habit.mood) == 1
