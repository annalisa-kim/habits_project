"""Tests that the predefined example data meets the assignment requirements."""

from datetime import datetime

from fixtures import get_default_habits
from analytics.progress import calculate_streak


def test_there_are_five_predefined_habits():
    assert len(get_default_habits()) == 5


def test_at_least_one_daily_and_one_weekly():
    periodicities = [h.periodicity for h in get_default_habits()]
    assert "daily" in periodicities
    assert "weekly" in periodicities


def test_each_habit_has_four_weeks_of_example_data():
    for habit in get_default_habits():
        assert habit.completions, f"{habit.name} has no example data"
        span_days = (datetime.now() - min(habit.completions)).days
        # Weekly habits span 4 weekly periods (>= ~21 days),
        # daily habits span ~4 weeks of days (>= ~26 days).
        minimum = 20 if habit.periodicity == "weekly" else 26
        assert span_days >= minimum, \
            f"{habit.name} spans only {span_days} days"


def test_fixture_streaks_are_plausible():
    habits = {h.name: h for h in get_default_habits()}
    assert calculate_streak(habits["Drink water"]) == 28   # perfect daily
    assert calculate_streak(habits["Workout"]) == 4        # perfect weekly
    assert calculate_streak(habits["Read 20 pages"]) < 28  # has gaps
