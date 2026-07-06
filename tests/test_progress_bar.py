"""Tests for the compact ■□ progress bar rendering."""

import matplotlib
matplotlib.use("Agg")  # main.py imports visuals → keep headless

from main import show_progress_bar


def test_bar_partial_progress():
    assert show_progress_bar(5, 8) == "■■■■■□□□ (5/8, 3 to go)"


def test_bar_goal_reached():
    assert show_progress_bar(3, 3) == "■■■ (3/3, done ✅)"


def test_bar_overachievement_never_overflows():
    assert show_progress_bar(6, 4) == "■■■■ (6/4, +2 extra)"


def test_bar_without_goal_does_not_crash():
    assert show_progress_bar(3, None) == "■■■ (3, no goal set)"


def test_bar_large_goal_is_scaled():
    bar = show_progress_bar(50, 100)
    assert bar.count("■") == 10 and bar.count("□") == 10
    assert "(50/100, 50 to go)" in bar
