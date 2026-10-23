"""SQLite persistence for yap2slay. Database location is read from DB_PATH per connection."""
from __future__ import annotations
import os, sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Kolkata"))
def _path() -> str:
    return os.getenv("DB_PATH", "planner.db")
def connect() -> sqlite3.Connection:
    path = _path()
    if path != ":memory:":
        Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init() -> None:
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, title TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'assignment', due_at TEXT NOT NULL, est_minutes INTEGER NOT NULL, done_minutes INTEGER NOT NULL DEFAULT 0, priority INTEGER NOT NULL DEFAULT 2, status TEXT NOT NULL DEFAULT 'todo');
        CREATE TABLE IF NOT EXISTS availability(id INTEGER PRIMARY KEY, date TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS blocks(id INTEGER PRIMARY KEY, task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE, start_at TEXT NOT NULL, end_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS actions(id INTEGER PRIMARY KEY, at TEXT NOT NULL, tool TEXT NOT NULL, summary TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS blocks_start_idx ON blocks(start_at);
        CREATE INDEX IF NOT EXISTS availability_date_idx ON availability(date);
        """)
def list_tasks(include_done: bool = False) -> list[dict]:
    init()
    with connect() as c:
        rows = c.execute("SELECT * FROM tasks" + ("" if include_done else " WHERE status != 'done'") + " ORDER BY due_at, id").fetchall()
    return [dict(r) for r in rows]
def get_blocks() -> list[dict]:
    init()
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT b.id,b.task_id,t.title,b.start_at,b.end_at FROM blocks b JOIN tasks t ON t.id=b.task_id ORDER BY b.start_at")]
def get_availability(date: str | None = None) -> list[dict]:
    init()
    with connect() as c:
        q="SELECT * FROM availability" + (" WHERE date=?" if date else "") + " ORDER BY date,start_time"
        return [dict(r) for r in c.execute(q, (date,) if date else ())]
def get_task(task_id: int) -> dict | None:
    init()
    with connect() as c:
        r=c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(r) if r else None
def actions_since(action_id: int) -> list[dict]:
    init()
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT id,tool,summary,at FROM actions WHERE id>? ORDER BY id", (int(action_id),))]
def latest_action_id() -> int:
    init()
    with connect() as c: return c.execute("SELECT COALESCE(MAX(id),0) FROM actions").fetchone()[0]
def clear_actions() -> None:
    """Clear activity history without changing tasks, availability, or schedule."""
    init()
    with connect() as c:
        c.execute("DELETE FROM actions")
def reset() -> None:
    """Clear planner rows only; never remove the SQLite file or unrelated files."""
    init()
    with connect() as c:
        c.execute("DELETE FROM blocks"); c.execute("DELETE FROM availability"); c.execute("DELETE FROM tasks"); c.execute("DELETE FROM actions")
def now_iso() -> str: return datetime.now(TZ).isoformat(timespec="seconds")
def log_action(c: sqlite3.Connection, tool: str, summary: str) -> None:
    c.execute("INSERT INTO actions(at,tool,summary) VALUES(?,?,?)", (now_iso(), tool, summary))
