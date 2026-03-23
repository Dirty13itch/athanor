"""SQLite persistence for the Governor task queue.
Uses WAL mode and timeout to handle concurrent access from dispatch loop + API.
"""
import sqlite3
import os
from datetime import datetime, timezone
import uuid

DB_PATH = os.environ.get("GOVERNOR_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "governor.db"))

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)  # 10s timeout for lock contention
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # WAL mode for concurrent reads+writes
    conn.execute("PRAGMA busy_timeout=5000")  # 5s busy wait
    return conn

def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        repo TEXT DEFAULT 'athanor',
        complexity TEXT DEFAULT 'medium',
        content_class TEXT DEFAULT 'cloud_safe',
        assigned_to TEXT,
        status TEXT DEFAULT 'queued',
        agent_session TEXT,
        worktree TEXT,
        created_at TEXT,
        started_at TEXT,
        completed_at TEXT,
        result TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS agent_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT,
        subscription TEXT,
        agent TEXT,
        session_name TEXT,
        started_at TEXT,
        completed_at TEXT,
        status TEXT DEFAULT 'running',
        tokens_used INTEGER DEFAULT 0
    )""")
    conn.commit()
    conn.close()

def add_task(title, description, repo="athanor", complexity="medium", content_class="cloud_safe"):
    conn = get_db()
    task_id = "task-" + datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
    conn.execute(
        "INSERT INTO tasks (id, title, description, repo, complexity, content_class, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (task_id, title, description, repo, complexity, content_class, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()
    return task_id

def get_queued_tasks(limit=10):
    conn = get_db()
    tasks = conn.execute("SELECT * FROM tasks WHERE status = 'queued' ORDER BY created_at LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(t) for t in tasks]

def get_all_tasks(limit=50):
    """Get all tasks ordered by creation time, most recent first."""
    conn = get_db()
    tasks = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(t) for t in tasks]

def get_stats():
    conn = get_db()
    stats = {
        "total": conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
        "queued": conn.execute("SELECT COUNT(*) FROM tasks WHERE status='queued'").fetchone()[0],
        "running": conn.execute("SELECT COUNT(*) FROM tasks WHERE status='running'").fetchone()[0],
        "done": conn.execute("SELECT COUNT(*) FROM tasks WHERE status='done'").fetchone()[0],
        "failed": conn.execute("SELECT COUNT(*) FROM tasks WHERE status='failed'").fetchone()[0],
    }
    conn.close()
    return stats

def update_task_status(task_id, status, assigned_to=None, result=None):
    """Update task status in SQLite."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    if assigned_to:
        conn.execute(
            "UPDATE tasks SET status=?, assigned_to=?, started_at=? WHERE id=?",
            (status, assigned_to, now, task_id)
        )
    elif result:
        conn.execute(
            "UPDATE tasks SET status=?, completed_at=?, result=? WHERE id=?",
            (status, now, result, task_id)
        )
    else:
        conn.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    conn.commit()
    conn.close()

def get_task_by_id(task_id):
    """Get a single task by ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

init_db()
