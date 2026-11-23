"""Analytics module implemented with a functional programming approach.

All functions in this module are pure: they take habits (and optionally areference datetime ``now``) as input and return values without mutating anystate. 
Streaks are computed by mapping completion timestamps onto calendar
*period indices* (days, ISO weeks, months or years) so that:

* completing a weekly habit on Monday and the next one on Friday of the following week still counts as consecutive weeks;
* several completions within the same period count only once;
* a missed period always breaks the streak.
"""

from datetime import datetime, timedelta, date
from functools import reduce


# ── Period helpers ──────────────────────────────────────────────────────────

def period_index(dt, periodicity):
    """Map a datetime/date onto a consecutive integer index for its period.

    Two completions belong to the same period iff they share the same index, and two periods are consecutive if their indices differ by exactly 1.

    Args:
        dt: A ``datetime`` or ``date`` of a completion.
        periodicity: One of ``"daily"``, ``"weekly"``, ``"monthly"``, ``"yearly"``.

    Returns:
        int: The period index.

    Raises:
        ValueError: If the periodicity is unknown.
    """
    d = dt.date() if isinstance(dt, datetime) else dt
    if periodicity == "daily":
        return d.toordinal()
    if periodicity == "weekly":
        # Ordinal of the Monday of the ISO week, divided by 7 → consecutive ints
        monday = d - timedelta(days=d.weekday())
        return monday.toordinal() // 7
    if periodicity == "monthly":
        return d.year * 12 + (d.month - 1)
    if periodicity == "yearly":
        return d.year
    raise ValueError(f"Unknown periodicity: {periodicity!r}")


def completed_periods(habit):
    """Return the sorted set of period indices in which the habit was completed."""
    return sorted(set(map(lambda dt: period_index(dt, habit.periodicity),
                          habit.completions)))


# ── Required analytics functions ────────────────────────────────────────────

def get_all_habit_names(habits):
    """Return the names of all currently tracked habits."""
    return list(map(lambda h: h.name, habits))


def get_habits_by_periodicity(habits, periodicity):
    """Return all habits that share the given periodicity."""
    return list(filter(lambda h: h.periodicity == periodicity, habits))


def calculate_streak(habit):
    """Return the longest run streak (consecutive periods) for a habit.

    A streak of ``x`` means the habit was completed in ``x`` consecutive
    periods (days for daily habits, ISO weeks for weekly habits, ...)
    without ever skipping a period.
    """
    periods = completed_periods(habit)
    if not periods:
        return 0

    def step(acc, idx_pair):
        """Extend or reset the running streak, tracking the best so far."""
        current, best = acc
        prev_idx, cur_idx = idx_pair
        current = current + 1 if cur_idx - prev_idx == 1 else 1
        return current, max(best, current)

    current, best = reduce(step, zip(periods, periods[1:]), (1, 1))
    return best


def get_longest_streak_for_habit(habit):
    """Return the longest run streak for a given habit (alias of calculate_streak)."""
    return calculate_streak(habit)


def get_habit_with_longest_streak(habits):
    """Return ``(habit, streak)`` for the habit with the longest run streak.

    Returns ``(None, 0)`` when no habits exist.
    """
    if not habits:
        return None, 0
    return max(map(lambda h: (h, calculate_streak(h)), habits),
               key=lambda pair: pair[1])


# ── Habit status ────────────────────────────────────────────────────────────

def get_current_streak(habit, now=None):
    """Return the streak that is still 'alive' at ``now``.

    Counts consecutive completed periods ending in the current period, or in
    the previous one (the current period is not over yet, so a habit
    completed yesterday but not yet today still has a live streak).
    """
    now = now or datetime.now()
    periods = set(completed_periods(habit))
    if not periods:
        return 0

    today_idx = period_index(now, habit.periodicity)
    start = today_idx if today_idx in periods else today_idx - 1

    streak = 0
    idx = start
    while idx in periods:
        streak += 1
        idx -= 1
    return streak



def is_broken(habit, now=None):
    """Return True if the habit missed at least one full period.

    A habit is broken when its last completion lies before the *previous*
    period relative to ``now`` (a habit never completed is broken as well).
    """
    now = now or datetime.now()
    periods = completed_periods(habit)
    if not periods:
        return True
    return period_index(now, habit.periodicity) - periods[-1] > 1


def get_broken_habits(habits, now=None):
    """Return all habits whose streak is currently broken."""
    now = now or datetime.now()
    return list(filter(lambda h: is_broken(h, now), habits))


# ── Period summaries ────────────────────────────────────────────────────────

def count_completions_in_period(habit, period="week", now=None):
    """Count how many times a habit was completed in the current day/week/month/year."""
    now = now or datetime.now()

    def in_period(dt):
        """True if the completion falls inside the current day/week/month/year."""
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        if period == "day":
            return dt.date() == now.date()
        if period == "week":
            return dt.isocalendar()[:2] == now.isocalendar()[:2]
        if period == "month":
            return (dt.year, dt.month) == (now.year, now.month)
        if period == "year":
            return dt.year == now.year
        return False

    return len(list(filter(in_period, habit.completions)))


def get_period_summary(habits, period="week", now=None):
    """Return ``(name, completions_in_current_period)`` for every habit."""
    now = now or datetime.now()
    return list(map(lambda h: (h.name, count_completions_in_period(h, period, now)),
                    habits))


# ── Shared habits ───────────────────────────────────────────────────────────

def get_member_contributions(habit, since=None):
    """Count completions per member for a (shared) habit.

    Pure function: given the habit's records (and an optional lower bound
    ``since``), returns ``[(user_id, count), ...]`` sorted by count,
    descending. The CLI maps user_ids to usernames for display.
    """
    relevant = filter(
        lambda r: since is None or r["timestamp"] >= since, habit.records)

    def step(acc, record):
        """Accumulate the per-user completion count."""
        uid = record["user_id"]
        acc[uid] = acc.get(uid, 0) + 1
        return acc

    counts = reduce(step, relevant, {})
    return sorted(counts.items(), key=lambda pair: pair[1], reverse=True)


#: Maps a habit periodicity onto the matching summary period name.
_PERIODICITY_TO_PERIOD = {"daily": "day", "weekly": "week",
                          "monthly": "month", "yearly": "year"}


def completions_in_current_period(habit, now=None):
    """Count check-offs in the habit's *own* current period.

    For a daily habit this is "how many times today" (e.g. 4 of 5 glasses
    of water), for a weekly habit "how many times this week", and so on.
    Used by the CLI to render the per-period progress bar next to the goal.
    """
    period = _PERIODICITY_TO_PERIOD.get(habit.periodicity, "day")
    return count_completions_in_period(habit, period, now)
