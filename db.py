"""SQLite persistence layer for users, habits, memberships and completions.

Schema (see the concept document, Figure 1):

* ``users``          – one row per account.
* ``habits``         – one row per habit (task spec + periodicity).
* ``habit_members``  – many-to-many link between users and habits. A habit
                       with one member is private; with 2+ members it is a
                       *shared* habit (e.g. household chores).
* ``completions``    – one row per check-off: who completed which habit when.

Change :data:`DB_NAME` (e.g. in tests) to point the module at a different
database file.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional

from habits.habit import Habit
from models.user import User

DB_NAME = "habits.db"


def connect():
    """Open a connection to the configured SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they do not exist."""
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                habit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                periodicity TEXT NOT NULL,
                category TEXT,
                goal INTEGER,
                start_date DATE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                progress INTEGER DEFAULT 0,
                badges TEXT,
                mood TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habit_members (
                habit_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (habit_id, user_id),
                FOREIGN KEY (habit_id) REFERENCES habits(habit_id)
                    ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS completions (
                completion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL,
                user_id INTEGER,
                timestamp DATETIME NOT NULL,
                FOREIGN KEY (habit_id) REFERENCES habits(habit_id)
                    ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        conn.commit()


# ── User management ─────────────────────────────────────────────────────────

def create_user(username: str, email: Optional[str] = None):
    """Insert a new user identified by a unique username."""
    with connect() as conn:
        conn.execute(
            "INSERT INTO users (username, email) VALUES (?, ?)",
            (username, email),
        )
        conn.commit()


def get_user_by_username(username: str) -> Optional[User]:
    """Return the User with the given username, or ``None`` if not found."""
    with connect() as conn:
        row = conn.execute(
            "SELECT user_id, username, email FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if row:
        return User(user_id=row[0], username=row[1], email=row[2])
    return None


# ── Membership (shared habits) ──────────────────────────────────────────────

def add_member(habit_id: int, user_id: int):
    """Link a user to a habit (idempotent). 2+ members = shared habit."""
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO habit_members (habit_id, user_id) VALUES (?, ?)",
            (habit_id, user_id),
        )
        conn.commit()


def remove_member(habit_id: int, user_id: int):
    """Unlink a user from a habit ("delete for me").

    When the last member leaves, the habit itself (and its completions,
    via ON DELETE CASCADE) is removed.
    """
    with connect() as conn:
        conn.execute(
            "DELETE FROM habit_members WHERE habit_id = ? AND user_id = ?",
            (habit_id, user_id),
        )
        remaining = conn.execute(
            "SELECT COUNT(*) FROM habit_members WHERE habit_id = ?",
            (habit_id,),
        ).fetchone()[0]
        if remaining == 0:
            conn.execute("DELETE FROM habits WHERE habit_id = ?", (habit_id,))
        conn.commit()


def get_members(habit_id: int):
    """Return ``[(user_id, username), ...]`` of all members of a habit."""
    with connect() as conn:
        rows = conn.execute("""
            SELECT u.user_id, u.username
            FROM habit_members m JOIN users u ON u.user_id = m.user_id
            WHERE m.habit_id = ?
            ORDER BY u.username
        """, (habit_id,)).fetchall()
    return rows


# ── Habit management ────────────────────────────────────────────────────────

def save_habit(habit: Habit, user_id: int):
    """Insert or update a habit and sync its completion records.

    On insert, ``user_id`` is registered as the first member. Completion
    records with an unknown author (``user_id`` is None, e.g. fixture data)
    are attributed to the saving user.
    """
    with connect() as conn:
        cursor = conn.cursor()
        # Prefer the primary key: it stays stable even when the habit is
        # renamed. Fall back to (name, user) for habits never saved before.
        if habit.habit_id is not None:
            row = (habit.habit_id,)
        else:
            row = cursor.execute("""
                SELECT h.habit_id FROM habits h
                JOIN habit_members m ON m.habit_id = h.habit_id
                WHERE h.name = ? AND m.user_id = ?
            """, (habit.name, user_id)).fetchone()

        payload = (
            habit.name, habit.periodicity, habit.category, habit.goal,
            habit.start_date.isoformat(), habit.created_at.isoformat(),
            habit.progress, json.dumps(habit.badges), json.dumps(habit.mood),
        )

        if row:
            habit.habit_id = row[0]
            cursor.execute("""
                UPDATE habits SET name = ?, periodicity = ?, category = ?,
                    goal = ?, start_date = ?, created_at = ?, progress = ?,
                    badges = ?, mood = ?
                WHERE habit_id = ?
            """, payload + (habit.habit_id,))
        else:
            cursor.execute("""
                INSERT INTO habits (name, periodicity, category, goal,
                    start_date, created_at, progress, badges, mood)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, payload)
            habit.habit_id = cursor.lastrowid
            cursor.execute(
                "INSERT OR IGNORE INTO habit_members (habit_id, user_id) "
                "VALUES (?, ?)", (habit.habit_id, user_id))

        # Sync completion records (source of truth: the Habit object)
        cursor.execute("DELETE FROM completions WHERE habit_id = ?",
                       (habit.habit_id,))
        cursor.executemany("""
            INSERT INTO completions (habit_id, user_id, timestamp)
            VALUES (?, ?, ?)
        """, [(habit.habit_id, r["user_id"] if r["user_id"] is not None
               else user_id, r["timestamp"].isoformat())
              for r in habit.records])

        habit.user_id = user_id
        conn.commit()


def _load_records(cursor, habit_id):
    """Load the completion records of a habit, oldest first."""
    rows = cursor.execute("""
        SELECT user_id, timestamp FROM completions
        WHERE habit_id = ? ORDER BY timestamp
    """, (habit_id,)).fetchall()
    return [{"user_id": r[0], "timestamp": datetime.fromisoformat(r[1])}
            for r in rows]


def load_habits(user_id: Optional[int] = None):
    """Load habits with their completion records and member lists.

    Args:
        user_id: If given, return every habit the user is a member of
            (own and shared); otherwise return all habits.

    Returns:
        list[Habit]
    """
    with connect() as conn:
        cursor = conn.cursor()
        base = """
            SELECT h.habit_id, h.name, h.periodicity, h.category, h.goal,
                   h.start_date, h.created_at, h.progress, h.badges, h.mood
            FROM habits h
        """
        if user_id:
            rows = cursor.execute(
                base + " JOIN habit_members m ON m.habit_id = h.habit_id"
                       " WHERE m.user_id = ? ORDER BY h.name",
                (user_id,)).fetchall()
        else:
            rows = cursor.execute(base + " ORDER BY h.name").fetchall()

        habits = []
        for r in rows:
            members = get_members(r[0])
            habit = Habit.from_dict({
                "habit_id": r[0], "name": r[1], "periodicity": r[2],
                "category": r[3], "goal": r[4], "start_date": r[5],
                "created_at": r[6], "progress": r[7],
                "badges": json.loads(r[8]) if r[8] else [],
                "mood": json.loads(r[9]) if r[9] else {},
                "user_id": user_id,
                "member_ids": [m[0] for m in members],
                "member_names": [m[1] for m in members],
            })
            habit.records = _load_records(cursor, r[0])
            habits.append(habit)
    return habits


def delete_habit(habit_id: int):
    """Delete a habit entirely, for all members (completions cascade)."""
    with connect() as conn:
        conn.execute("DELETE FROM habits WHERE habit_id = ?", (habit_id,))
        conn.commit()
