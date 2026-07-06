"""Optional matplotlib charts for habit completions."""

from collections import defaultdict
from datetime import datetime

import matplotlib.pyplot as plt

#: Accepted aliases for period names → canonical form used internally.
_PERIOD_ALIASES = {
    "day": "day", "daily": "day",
    "week": "week", "weekly": "week",
    "month": "month", "monthly": "month",
    "year": "year", "yearly": "year",
}


def _normalize_period(period):
    """Map any accepted alias ('week', 'weekly', ...) to its canonical name."""
    return _PERIOD_ALIASES.get(period)


def show_completions_by_category(habits):
    """Show a bar chart with the number of completions per category."""
    category_counts = defaultdict(int)
    for habit in habits:
        category_counts[habit.category or "Uncategorized"] += len(habit.completions)

    if not category_counts:
        print("⚠️ No data available for chart.")
        return

    plt.figure(figsize=(10, 6))
    plt.bar(list(category_counts.keys()), list(category_counts.values()),
            color="skyblue")
    plt.title("Completions by Category")
    plt.xlabel("Category")
    plt.ylabel("Number of Completions")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def show_completions_by_period(habits, period="week"):
    """Show a line chart of completions grouped by day/week/month/year.

    Args:
        habits: List of Habit objects.
        period: ``"day"``/``"daily"``, ``"week"``/``"weekly"``,
            ``"month"``/``"monthly"`` or ``"year"``/``"yearly"``.
    """
    period = _normalize_period(period)
    if period is None:
        print("⚠️ Invalid period.")
        return

    period_counts = defaultdict(int)
    for habit in habits:
        for dt in habit.completions:
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt)
            d = dt.date()
            if period == "day":
                key = d.isoformat()
            elif period == "week":
                iso = d.isocalendar()
                key = f"{iso[0]}-W{iso[1]:02d}"
            elif period == "month":
                key = d.strftime("%Y-%m")
            else:  # year
                key = str(d.year)
            period_counts[key] += 1

    if not period_counts:
        print("⚠️ No data available for chart.")
        return

    labels, counts = zip(*sorted(period_counts.items()))
    plt.figure(figsize=(12, 6))
    plt.plot(labels, counts, marker="o", linestyle="-", color="green")
    plt.title(f"Completions per {period.capitalize()}")
    plt.xlabel(period.capitalize())
    plt.ylabel("Number of Completions")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.show()
