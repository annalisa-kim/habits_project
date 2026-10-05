# Tracksy 🌟 — A CLI Habit Tracker

Tracksy is a Python backend for a habit tracking app.
Users create habits with a task specification and a eriodicity (daily, weekly, monthly or yearly), check them off over time, and analyse their progress: 
streaks, broken habits, completions per period, plus optional charts, badges and mood tracking.

## Features

- Multi-user support (simple username login/registration)
- Shared habits: share a habit (e.g. household chores) with other
  users; every member sees it, any member can check it off, the streak
  belongs to the group, and analytics show who contributed most
- Create, complete ("check off") and delete habits
- Daily and weekly habits (plus monthly and yearly)
- Streak computation based on calendar periods (days / ISO weeks / months / years)
- Analytics module written in a functional programming style:
  - list all tracked habits
  - list habits by periodicity
  - longest run streak across all habits
  - longest run streak for a given habit
  - broken habits, current streaks, completions per period
  - member contributions for shared habits
- Persistence with SQLite (`sqlite3`, standard library)
- Optional matplotlib charts, badges and mood history
- Unit test suite (pytest)

## Project structure

```
tracksy/
├── analytics/
│   ├── progress.py       # Functional analytics (streaks, filters, summaries)
│   └── visuals.py        # Optional matplotlib charts
├── habits/
│   └── habit.py          # Habit class (OOP core)
├── models/
│   └── user.py           # User class
├── tests/                # Pytest unit test suite
├── conftest.py           # Makes the project root importable in the tests
├── db.py                 # SQLite persistence layer
├── fixtures.py           # 5 predefined habits + 4 weeks of example data
├── load_fixtures.py      # Script that loads the example data into the DB
├── main.py               # CLI entry point (interactive menu)
├── README.md             # This documentation
└── requirements.txt      # Dependencies (matplotlib, pytest)
```

## Installation

Requires **Python 3.7+** (tested with 3.10–3.12).

```bash
# 1. Clone / unzip the project, then from the project root:
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
```

## Quick start

```bash
# (Optional) load the 5 predefined habits with 4 weeks of example data
python load_fixtures.py

# Start the app
python main.py
```

At startup, enter a username to log in (a new username registers you automatically). 
To explore the predefined example data, log in as **demo** after running `load_fixtures.py`.

### Example session

```
👤 Welcome to Tracksy!
Enter your username: demo
✅ Welcome back, demo!

🌟 What do you want to do?
1. ➕ Create habit
2. ✏️ Edit habit
3. ✅ Track progress
4. 📋 Show habits
5. 🤝 Share habit
6. 📊 Analytics
7. 💪 Show mood history
8. 🎖️ Show badges
9. 🗑️ Delete habit
10. 👋 Exit
```

- **Create a habit**: choose option `1`, enter a name, pick a periodicity (daily/weekly/monthly/yearly), a category and an optional per-period goal.
- **Edit a habit**: choose option `2`
- **Complete a task**: choose option `3` and select the habit to check off.
  The completion timestamp — and who completed it — is recorded automatically.
- **Share a habit**: choose option `5`, pick the habit and enter the other user's username (they must have logged in at least once). 
  The habit then appears in their list too, marked `🤝 shared with: ...`, and any member can check it off. 
  Deleting a shared habit removes it only for you; the habit disappears entirely when the last member leaves it.
- **Analyse your habits**: choose option `6`; from there you can list habits, filter by periodicity, view longest streaks, spot broken habits, see member contributions for shared habits and plot charts.

### Trying shared habits with the demo data

`load_fixtures.py` also creates a second user (**sam**) and a shared weekly habit *Clean the bathroom* completed alternately by `demo` and `sam` over 4 weeks. 
Log in as `demo` (or `sam`) and choose Show habits — the habit is marked as shared:

```
- Clean the bathroom (weekly) 🤝 shared with: sam 🔥 4-week streak
  ■ (1/1, done ✅) this week
```

In the *Analytics* menu, option `7` shows who contributed:

```
📊 Contributions for 'Clean the bathroom':
- sam: 2
- demo: 2
```

To share one of your own habits, use menu option `4` and enter the other user's username. 
The other user must already be registered — it is enough that they logged in once with their username. 
For example, while logged in as `demo` you can share a habit with `sam`; sam will see it in their list at the next login, and any check-off by either user counts for the group.

## Running the tests

```bash
python -m pytest tests/ -v
```

The suite covers habit creation and tracking, the streak/analytics logic (including edge cases such as skipped periods and multiple completions in the same period),
the SQLite layer (on a temporary database), the predefined fixture data, and the shared-habit behaviour: membership, visibility for all members, per-member completion records, group streaks with alternating completers, member contributions and the "delete only for me" semantics.

## Design notes

- The **`Habit` class** encapsulates the task specification, periodicity, creation timestamp and the completion records (OOP). 
  Each record stores who completed the task and when, which is what makes shared habits possible; `habit.completions` stays available as a derived property so the analytics functions work identically for private and shared habits.
- The **database schema** mirrors the domain: `users`, `habits`, `habit_members` (many-to-many link — 2+ members = shared habit) and `completions` (one row per check-off). 
  A member leaving a shared habit only removes their membership; the habit is deleted when the last member leaves.
- The **analytics module** contains only pure functions operating on habit lists (`map`/`filter`/`reduce`), which makes them easy to test and reason about.
- **Streaks** are computed by mapping completions to calendar period indices, so completing a weekly habit on Monday and then on Friday of the following week still counts as two consecutive weeks, while multiple completions in the same period count once.
