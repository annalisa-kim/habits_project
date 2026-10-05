"""Predefined habits with 4 weeks of example tracking data (test fixture).
The assignment requires 5 predefined habits (at least one daily and one weekly) each with 4 weeks of example data. 
The data is generated relative to "today" so streaks and analytics always look realistic, and includes intentional gaps so that broken habits and partial streaks can be observed and tested.
"""

from datetime import datetime, timedelta

from habits.habit import Habit


def _days_ago(days, hour=8):
    """Return a datetime ``days`` days before today, at the given hour."""
    base = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
    return base - timedelta(days=days)


def get_default_habits():
    """Return the 5 predefined habits, each with 4 weeks of example data.

    * ``Drink water``  – daily,  perfect 28-day streak (twice a day).
    * ``Read 20 pages`` – daily,  a few missed days (broken streaks).
    * ``Meditate``      – daily,  completed only on some days.
    * ``Workout``       – weekly, perfect 4-week streak.
    * ``Review goals``  – weekly, one skipped week (broken streak).
    """
    today = datetime.now()

    # Daily, perfect: every day for 28 days, morning and evening
    drink_water = Habit(
        name="Drink water", periodicity="daily", category="Health", goal=2,
        start_date=(today - timedelta(days=28)).date(),
        completions=[_days_ago(d, hour=h) for d in range(28) for h in (8, 20)],
    )

    # Daily, imperfect: missed days 5, 6 and 14 → longest run of 13 days
    read = Habit(
        name="Read 20 pages", periodicity="daily", category="Study", goal=1,
        start_date=(today - timedelta(days=28)).date(),
        completions=[_days_ago(d, hour=21)
                     for d in range(28) if d not in (5, 6, 14)],
    )

    # Daily, sparse: roughly every other day
    meditate = Habit(
        name="Meditate", periodicity="daily", category="Personal", goal=1,
        start_date=(today - timedelta(days=28)).date(),
        completions=[_days_ago(d, hour=7) for d in range(0, 28, 2)],
    )

    # Weekly, perfect: once per week for 4 consecutive weeks
    workout = Habit(
        name="Workout", periodicity="weekly", category="Fitness", goal=3,
        start_date=(today - timedelta(weeks=4)).date(),
        completions=[_days_ago(7 * w, hour=18) for w in range(4)],
    )

    # Weekly, imperfect: week 2 skipped
    review_goals = Habit(
        name="Review goals", periodicity="weekly", category="Work", goal=1,
        start_date=(today - timedelta(weeks=4)).date(),
        completions=[_days_ago(7 * w, hour=10) for w in (0, 1, 3)],
    )

    habits = [drink_water, read, meditate, workout, review_goals]
    for habit in habits:
        habit.progress = len(habit.completions)
    return habits
