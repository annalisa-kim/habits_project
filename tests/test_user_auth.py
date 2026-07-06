"""Tests for user creation and retrieval, on a temporary database."""

import os
import tempfile

import db
from db import init_db, create_user, get_user_by_username

_ORIGINAL_DB = db.DB_NAME
_TMP_DB = None


def setup_module(module):
    global _TMP_DB
    fd, _TMP_DB = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(_TMP_DB)
    db.DB_NAME = _TMP_DB
    init_db()


def teardown_module(module):
    db.DB_NAME = _ORIGINAL_DB
    if _TMP_DB and os.path.exists(_TMP_DB):
        os.remove(_TMP_DB)


def test_create_and_retrieve_user():
    create_user("testuser", "test@example.com")
    user = get_user_by_username("testuser")
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.user_id is not None


def test_unknown_user_returns_none():
    assert get_user_by_username("ghost") is None
