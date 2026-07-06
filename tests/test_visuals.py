"""Smoke tests for the matplotlib charts (run headless, no windows)."""

import matplotlib
matplotlib.use("Agg")  # headless backend: no GUI windows during tests
import matplotlib.pyplot as plt

from analytics.visuals import (show_completions_by_period,
                               show_completions_by_category)
from fixtures import get_default_habits


def teardown_function(function):
    plt.close("all")


def test_chart_by_category_runs_without_error():
    show_completions_by_category(get_default_habits())


def test_chart_by_period_accepts_both_naming_conventions():
    habits = get_default_habits()
    show_completions_by_period(habits, "week")    # canonical
    show_completions_by_period(habits, "weekly")  # alias (periodicity style)
