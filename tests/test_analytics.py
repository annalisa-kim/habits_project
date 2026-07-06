"""Unit tests for the functional analytics module (streaks, filters, status)."""

from datetime import datetime, timedelta

from habits.habit import Habit
from analytics.progress import (
    calculate_streak, get_longest_streak_for_habit,
    get_habit_with_longest_streak, get_all_habit_names,
    get_habits_by_periodicity, is_broken, get_broken_habits,
    get_current_streak, count_completions_in_period, get_period_summary,
)

NOW = datetime(2026, 7, 6, 12, 0)  # a Monday


def daily_habit(days, name="d"):
    """Daily habit completed on the given offsets (days before NOW)."""
    return Habit(name=name, periodicity="daily",
                 completions=[NOW - timedelta(days=d) for d in days])


def weekly_habit(dates, name="w"):
    return Habit(name=name, periodicity="weekly", completions=dates)


# ── calculate_streak ────────────────────────────────────────────────────────

def test_streak_empty_habit_is_zero():
    assert calculate_streak(Habit(name="x", periodicity="daily")) == 0


def test_streak_daily_consecutive_days():
    assert calculate_streak(daily_habit([0, 1, 2, 3, 4])) == 5


def test_streak_daily_gap_breaks_streak():
    # Completed on days -4, -3, then a gap, then day 0
    assert calculate_streak(daily_habit([0, 3, 4])) == 2


def test_streak_daily_multiple_completions_same_day_count_once():
    habit = Habit(name="x", periodicity="daily", completions=[
        NOW.replace(hour=8), NOW.replace(hour=20),        # same day, twice
        NOW - timedelta(days=1),
    ])
    assert calculate_streak(habit) == 2


def test_streak_weekly_counts_iso_weeks_regardless_of_weekday():
    # Monday W28, Friday W29, Tuesday W30 → 3 consecutive ISO weeks
    habit = weekly_habit([
        datetime(2026, 7, 6, 9),    # Monday, week 28
        datetime(2026, 7, 17, 18),  # Friday, week 29
        datetime(2026, 7, 21, 7),   # Tuesday, week 30
    ])
    assert calculate_streak(habit) == 3


def test_streak_weekly_skipped_week_breaks_streak():
    habit = weekly_habit([
        datetime(2026, 6, 22, 9),   # week 26
        datetime(2026, 7, 6, 9),    # week 28 (week 27 skipped)
    ])
    assert calculate_streak(habit) == 1


def test_longest_streak_for_habit_alias():
    habit = daily_habit([0, 1, 2])
    assert get_longest_streak_for_habit(habit) == calculate_streak(habit)


def test_habit_with_longest_streak_across_habits():
    short = daily_habit([0, 2], name="short")
    long = daily_habit([0, 1, 2, 3], name="long")
    best, streak = get_habit_with_longest_streak([short, long])
    assert best.name == "long"
    assert streak == 4


def test_habit_with_longest_streak_empty_list():
    assert get_habit_with_longest_streak([]) == (None, 0)


# ── Filters ─────────────────────────────────────────────────────────────────

def test_get_all_habit_names():
    habits = [daily_habit([], name="a"), daily_habit([], name="b")]
    assert get_all_habit_names(habits) == ["a", "b"]


def test_get_habits_by_periodicity():
    daily = daily_habit([], name="daily1")
    weekly = weekly_habit([], name="weekly1")
    assert get_habits_by_periodicity([daily, weekly], "daily") == [daily]
    assert get_habits_by_periodicity([daily, weekly], "weekly") == [weekly]


# ── Broken habits & current streak ──────────────────────────────────────────

def test_is_broken_daily():
    fresh = daily_habit([0])              # completed today
    yesterday = daily_habit([1])          # still alive
    stale = daily_habit([3])              # missed 2 full days
    empty = Habit(name="e", periodicity="daily")
    assert is_broken(fresh, NOW) is False
    assert is_broken(yesterday, NOW) is False
    assert is_broken(stale, NOW) is True
    assert is_broken(empty, NOW) is True


def test_get_broken_habits_filters():
    good, bad = daily_habit([0], name="good"), daily_habit([5], name="bad")
    assert get_broken_habits([good, bad], NOW) == [bad]


def test_current_streak_daily():
    assert get_current_streak(daily_habit([0, 1, 2]), NOW) == 3
    # Not completed today, but yesterday: streak still alive
    assert get_current_streak(daily_habit([1, 2]), NOW) == 2
    # Broken two days ago: no live streak
    assert get_current_streak(daily_habit([3, 4]), NOW) == 0


# ── Period summaries ────────────────────────────────────────────────────────

def test_count_completions_in_period():
    habit = daily_habit([0, 1, 40])
    assert count_completions_in_period(habit, "week", NOW) >= 1
    assert count_completions_in_period(habit, "year", NOW) == 3


def test_get_period_summary_returns_pairs():
    habits = [daily_habit([0], name="a"), daily_habit([], name="b")]
    summary = dict(get_period_summary(habits, "day", NOW))
    assert summary == {"a": 1, "b": 0}


def test_completions_in_current_period_uses_habit_periodicity():
    from analytics.progress import completions_in_current_period
    # Daily habit: 4 glasses today + old ones → 4 today
    water = Habit(name="Water", periodicity="daily", goal=5, completions=[
        NOW.replace(hour=h) for h in (8, 11, 15, 19)
    ] + [NOW - timedelta(days=3)])
    assert completions_in_current_period(water, NOW) == 4

    # Weekly habit: 1 this ISO week, 1 three weeks ago → 1 this week
    gym = Habit(name="Gym", periodicity="weekly", goal=3,
                completions=[NOW, NOW - timedelta(weeks=3)])
    assert completions_in_current_period(gym, NOW) == 1
