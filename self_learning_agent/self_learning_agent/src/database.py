"""SQLite: visible chat transcript, retrieved-memory log, and feedback records."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from src.config import SQLITE_PATH


@contextmanager
def _conn():
    con = sqlite3.connect(SQLITE_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations(
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER,
                role TEXT, content TEXT, retrieved_memories TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS feedback(
                id INTEGER PRIMARY KEY AUTOINCREMENT, message_id INTEGER UNIQUE,
                rating INTEGER, comment TEXT, created_at TEXT);
            """
        )


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def create_conversation(title: str = "New chat") -> int:
    with _conn() as c:
        return c.execute("INSERT INTO conversations(title, created_at) VALUES(?,?)", (title, _now())).lastrowid


def rename_conversation(conv_id: int, title: str) -> None:
    with _conn() as c:
        c.execute("UPDATE conversations SET title=? WHERE id=?", (title[:50], conv_id))


def list_conversations() -> list[dict]:
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM conversations ORDER BY id DESC")]


def add_message(conv_id: int, role: str, content: str, retrieved: list[dict] | None = None) -> int:
    with _conn() as c:
        return c.execute(
            "INSERT INTO messages(conversation_id, role, content, retrieved_memories, created_at) VALUES(?,?,?,?,?)",
            (conv_id, role, content, json.dumps(retrieved or []), _now()),
        ).lastrowid


def get_messages(conv_id: int, limit: int | None = None) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            """SELECT m.*, f.rating AS rating FROM messages m
               LEFT JOIN feedback f ON f.message_id = m.id
               WHERE m.conversation_id=? ORDER BY m.id""",
            (conv_id,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["retrieved_memories"] = json.loads(d["retrieved_memories"] or "[]")
        out.append(d)
    return out[-limit:] if limit else out


def get_message(message_id: int) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
    return dict(r) if r else None


def get_previous_user_message(message_id: int) -> str:
    """The user question that came right before an assistant message."""
    m = get_message(message_id)
    if not m:
        return ""
    with _conn() as c:
        r = c.execute(
            "SELECT content FROM messages WHERE conversation_id=? AND id<? AND role='user' ORDER BY id DESC LIMIT 1",
            (m["conversation_id"], message_id),
        ).fetchone()
    return r["content"] if r else ""


def save_feedback(message_id: int, rating: int, comment: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO feedback(message_id, rating, comment, created_at) VALUES(?,?,?,?)",
            (message_id, rating, comment, _now()),
        )
