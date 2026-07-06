"""Core domain model: the Habit class."""

from datetime import datetime


class Habit:
    """A habit with a task specification, a periodicity and its tracking data.

    A habit can be *shared*: it may belong to several users (household
    members). Every check-off is stored as a record ``(user_id, timestamp)``
    so the app knows both *when* and *by whom* a task was completed. Streaks
    always belong to the whole group of members.

    Attributes:
        name: Short task specification, e.g. ``"Clean the bathroom"``.
        periodicity: ``"daily"``, ``"weekly"``, ``"monthly"`` or ``"yearly"``.
        category: Optional grouping label (e.g. ``"Health"``).
        goal: Optional number of completions the user aims for per period.
        start_date: The date the user wants to start tracking.
        created_at: Timestamp of when the habit was created.
        records: List of check-off records ``{"user_id": int|None,
            "timestamp": datetime}``, one per completion.
        progress: Total number of check-offs.
        badges: List of badge labels unlocked for this habit.
        mood: Mapping ISO-timestamp → mood emoji recorded by the user.
        habit_id: Database primary key (``None`` until first saved).
        user_id: User who created / loaded the habit.
        member_ids: user_ids of all members (populated when loaded from DB).
        member_names: usernames of all members (populated when loaded from DB).
    """

    def __init__(
        self,
        name,
        periodicity,
        category=None,
        goal=None,
        start_date=None,
        created_at=None,
        completions=None,
        records=None,
        progress=0,
        badges=None,
        mood=None,
        habit_id=None,
        user_id=None,
        member_ids=None,
        member_names=None,
    ):
        self.name = name
        self.periodicity = periodicity
        self.category = category
        self.goal = goal
        self.start_date = start_date or datetime.now().date()
        self.created_at = created_at or datetime.now()
        # ``records`` is the source of truth; a plain list of datetimes can
        # still be passed via ``completions`` for convenience (owner unknown).
        self.records = list(records) if records else []
        if completions:
            self.records.extend({"user_id": None, "timestamp": dt}
                                for dt in completions)
        self.records.sort(key=lambda r: r["timestamp"])
        self.progress = progress
        self.badges = badges or []
        self.mood = mood or {}
        self.habit_id = habit_id
        self.user_id = user_id
        self.member_ids = member_ids or []
        self.member_names = member_names or []

    # ── Derived attributes ──────────────────────────────────────────────

    @property
    def completions(self):
        """The completion timestamps (all members), sorted ascending.

        Kept as a property so the analytics module can keep operating on a
        plain list of ``datetime`` objects, whether the habit is private or
        shared.
        """
        return [r["timestamp"] for r in self.records]

    @property
    def shared(self):
        """True if the habit has two or more members."""
        return len(self.member_ids) > 1

    @property
    def completed_today(self):
        """True if any member checked the habit off today.

        Computed from the records instead of being stored, so it can never
        go stale between sessions.
        """
        today = datetime.now().date()
        return any(r["timestamp"].date() == today for r in self.records)

    # ── Behaviour ───────────────────────────────────────────────────────

    def complete(self, user_id=None, when=None):
        """Check off the habit's task.

        Args:
            user_id: The member who completed the task (``None`` if unknown).
            when: Optional ``datetime`` of the completion (defaults to now).
        """
        self.records.append({"user_id": user_id,
                             "timestamp": when or datetime.now()})
        self.progress += 1

    # ── Serialization ───────────────────────────────────────────────────

    def to_dict(self):
        """Serialize the habit to a JSON-friendly dictionary."""
        return {
            "habit_id": self.habit_id,
            "user_id": self.user_id,
            "name": self.name,
            "periodicity": self.periodicity,
            "category": self.category,
            "goal": self.goal,
            "start_date": self.start_date.isoformat(),
            "created_at": self.created_at.isoformat(),
            "records": [{"user_id": r["user_id"],
                         "timestamp": r["timestamp"].isoformat()}
                        for r in self.records],
            "progress": self.progress,
            "badges": self.badges,
            "mood": self.mood,
            "member_ids": self.member_ids,
            "member_names": self.member_names,
        }

    @staticmethod
    def from_dict(data):
        """Rebuild a Habit from a dictionary produced by :meth:`to_dict`.

        Also accepts the legacy format where ``completions`` is a plain list
        of ISO timestamps without user information.
        """
        records = [{"user_id": r.get("user_id"),
                    "timestamp": datetime.fromisoformat(r["timestamp"])}
                   for r in data.get("records", [])]
        legacy = [datetime.fromisoformat(dt)
                  for dt in data.get("completions", [])]
        return Habit(
            name=data["name"],
            periodicity=data["periodicity"],
            category=data.get("category"),
            goal=data.get("goal"),
            start_date=datetime.fromisoformat(data["start_date"]).date()
            if data.get("start_date") else None,
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at") else None,
            records=records,
            completions=legacy,
            progress=data.get("progress", 0),
            badges=data.get("badges", []),
            mood=data.get("mood", {}),
            habit_id=data.get("habit_id"),
            user_id=data.get("user_id"),
            member_ids=data.get("member_ids", []),
            member_names=data.get("member_names", []),
        )

    def __repr__(self):
        kind = "shared" if self.shared else "private"
        return f"<Habit name={self.name!r} periodicity={self.periodicity!r} {kind}>"
