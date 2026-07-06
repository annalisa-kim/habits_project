"""Load the predefined example habits into the database for a demo user.

Besides the 5 required predefined habits, this script also creates a second user ('sam') and a demo *shared* habit ("Clean the bathroom") completed by both users over 4 weeks, so the shared-habit features can be explored immediately.

Usage:
    python load_fixtures.py
"""

from datetime import datetime, timedelta

from db import (init_db, save_habit, create_user, get_user_by_username,
                add_member)
from fixtures import get_default_habits
from habits.habit import Habit

DEMO_USERNAME = "demo"
ROOMMATE_USERNAME = "sam"


def _ensure_user(username, email):
    """Return the user with this username, creating it if needed."""
    user = get_user_by_username(username)
    if user is None:
        create_user(username, email)
        user = get_user_by_username(username)
    return user


def _shared_demo_habit(demo_id, sam_id):
    """A weekly chore completed alternately by demo and sam over 4 weeks."""
    base = datetime.now().replace(hour=11, minute=0, second=0, microsecond=0)
    habit = Habit(
        name="Clean the bathroom", periodicity="weekly",
        category="Home", goal=1,
        start_date=(base - timedelta(weeks=4)).date(),
    )
    completers = [demo_id, sam_id, demo_id, sam_id]
    for week, uid in enumerate(completers):
        habit.complete(user_id=uid, when=base - timedelta(weeks=week))
    return habit


def load_fixtures():
    """Create demo users, the 5 predefined habits and one shared habit."""
    init_db()
    demo = _ensure_user(DEMO_USERNAME, "demo@example.com")
    sam = _ensure_user(ROOMMATE_USERNAME, "sam@example.com")

    for habit in get_default_habits():
        save_habit(habit, demo.user_id)

    shared = _shared_demo_habit(demo.user_id, sam.user_id)
    save_habit(shared, demo.user_id)
    add_member(shared.habit_id, sam.user_id)

    print(f"✅ 5 default habits loaded for '{DEMO_USERNAME}', plus 1 shared "
          f"habit ('{shared.name}') between '{DEMO_USERNAME}' and "
          f"'{ROOMMATE_USERNAME}'. Log in as either user to explore.")


if __name__ == "__main__":
    load_fixtures()
