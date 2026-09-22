import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger("economy")

DB_PATH = Path("ktun_economy.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            credits INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_credit(user_id: str, amount: int = 1):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (user_id, credits)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET credits = credits + ?
    ''', (str(user_id), amount, amount))
    conn.commit()
    conn.close()
    logger.info(f"Added {amount} credits to user {user_id}")

def spend_credit(user_id: str, amount: int = 1) -> bool:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT credits FROM users WHERE user_id = ?', (str(user_id),))
    row = cursor.fetchone()
    if row and row[0] >= amount:
        cursor.execute('UPDATE users SET credits = credits - ? WHERE user_id = ?', (amount, str(user_id)))
        conn.commit()
        conn.close()
        logger.info(f"User {user_id} spent {amount} credits")
        return True
    conn.close()
    return False

def get_credits(user_id: str) -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT credits FROM users WHERE user_id = ?', (str(user_id),))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0
