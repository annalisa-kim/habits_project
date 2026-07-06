"""User domain model."""

from datetime import datetime
from typing import Optional


class User:
    """An account identified by a unique username.

    Attributes:
        user_id: Database primary key (``None`` until first saved).
        username: Unique login name.
        email: Optional contact e-mail.
        created_at: Timestamp of registration.
    """

    def __init__(self, user_id: Optional[int] = None, username: str = "",
                 email: Optional[str] = None,
                 created_at: Optional[datetime] = None):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.created_at = created_at or datetime.now()

    def __repr__(self):
        return f"<User username={self.username!r} id={self.user_id}>"
