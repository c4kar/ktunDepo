import pytest
import os
import sqlite3
from pathlib import Path
from agent.economy import add_credit, spend_credit, get_credits, init_db, DB_PATH

@pytest.fixture(autouse=True)
def run_around_tests():
    # Setup
    if DB_PATH.exists():
        os.remove(DB_PATH)
    init_db()
    yield
    # Teardown
    if DB_PATH.exists():
        os.remove(DB_PATH)

def test_add_credit():
    add_credit("user123")
    assert get_credits("user123") == 1
    add_credit("user123", 2)
    assert get_credits("user123") == 3

def test_spend_credit():
    add_credit("user456", 2)
    # Successful spend
    assert spend_credit("user456", 1) == True
    assert get_credits("user456") == 1
    # Unsuccessful spend (not enough credits)
    assert spend_credit("user456", 2) == False
    assert get_credits("user456") == 1

def test_unknown_user_credits():
    assert get_credits("unknown") == 0
    assert spend_credit("unknown", 1) == False
