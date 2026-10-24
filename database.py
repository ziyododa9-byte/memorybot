"""
Database operations for MemoryBot
SQLite-based storage for notes and reminders
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional


DB_PATH = "memorybot.db"


def init_db():
    """Initialize database tables"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Notes table
    c.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Reminders table
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            notified_day_before INTEGER DEFAULT 0,
            notified_30min INTEGER DEFAULT 0,
            notified_main INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
#  NOTES
# ─────────────────────────────────────────────

def save_note(user_id: int, title: str, content: str, tags: list = None) -> int:
    """Save a note and return its ID"""
    now = datetime.now().isoformat()
    tags_json = json.dumps(tags or [], ensure_ascii=False)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO notes (user_id, title, content, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, title, content, tags_json, now, now)
    )
    note_id = c.lastrowid
    conn.commit()
    conn.close()
    return note_id


def get_all_notes(user_id: int) -> list[dict]:
    """Get all notes for a user"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_note(user_id: int, note_id: int) -> bool:
    """Delete a note by ID"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ─────────────────────────────────────────────
#  REMINDERS
# ─────────────────────────────────────────────

def save_reminder(user_id: int, task: str, remind_at: datetime) -> int:
    """Save a reminder and return its ID"""
    now = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO reminders (user_id, task, remind_at, created_at) VALUES (?, ?, ?, ?)",
        (user_id, task, remind_at.isoformat(), now)
    )
    reminder_id = c.lastrowid
    conn.commit()
    conn.close()
    return reminder_id


def get_pending_reminders() -> list[dict]:
    """Get all reminders that haven't been fully notified yet"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT * FROM reminders
        WHERE notified_main = 0
        ORDER BY remind_at ASC
    """)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_reminders(user_id: int) -> list[dict]:
    """Get all upcoming reminders for a user"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT * FROM reminders
        WHERE user_id = ? AND notified_main = 0
        ORDER BY remind_at ASC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_notified(reminder_id: int, field: str):
    """Mark a reminder notification as sent"""
    allowed = {"notified_day_before", "notified_30min", "notified_main"}
    if field not in allowed:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"UPDATE reminders SET {field} = 1 WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()


def delete_reminder(user_id: int, reminder_id: int) -> bool:
    """Delete a reminder"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted
