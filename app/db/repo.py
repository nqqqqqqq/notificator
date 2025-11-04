# app/db/repo.py
import sqlite3
import time
from pathlib import Path

# ---- единый абсолютный путь к БД (рядом с файлом repo.py) ----
DB_PATH = Path(__file__).with_name("database.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- авто-создание/миграции: добавим sleep_started_at если нет ---
def _ensure_schema():
    conn = get_connection()
    cur = conn.cursor()

    # --- users ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_user_id  INTEGER NOT NULL UNIQUE,
        username          TEXT,
        timezone          TEXT DEFAULT 'Europe/Warsaw',
        is_sleeping       INTEGER NOT NULL DEFAULT 0,
        sleep_started_at  REAL,
        created_at        TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at        TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # --- tasks ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id            INTEGER NOT NULL,
        task_name          TEXT NOT NULL,
        task_note          TEXT,
        status             INTEGER NOT NULL DEFAULT 1 CHECK (status IN (0,1)),
        next_reminder_at   REAL NOT NULL,
        interval           INTEGER NOT NULL,
        paused_until       REAL,
        is_one_shot        INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # --- миграции (если таблицы уже существуют без нужных колонок) ---
    # users: sleep_started_at
    cur.execute("PRAGMA table_info(users)")
    u_cols = [r[1] for r in cur.fetchall()]
    if "sleep_started_at" not in u_cols:
        try:
            cur.execute("ALTER TABLE users ADD COLUMN sleep_started_at REAL")
        except Exception:
            pass

    # tasks: is_one_shot
    cur.execute("PRAGMA table_info(tasks)")
    t_cols = [r[1] for r in cur.fetchall()]
    if "is_one_shot" not in t_cols:
        try:
            cur.execute("ALTER TABLE tasks ADD COLUMN is_one_shot INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass

    # индексы
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_tasks_status_user_time
    ON tasks(status, user_id, next_reminder_at)
    """)

    conn.commit()
    conn.close()

_ensure_schema()

# ---- users ----
def get_or_create_user(telegram_user_id, username=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_user_id = ?", (telegram_user_id,))
    user = cur.fetchone()
    if user:
        conn.close()
        return user
    cur.execute("INSERT INTO users (telegram_user_id, username) VALUES (?, ?)", (telegram_user_id, username))
    conn.commit()
    cur.execute("SELECT * FROM users WHERE telegram_user_id = ?", (telegram_user_id,))
    user = cur.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

# ---- tasks ----
def add_task(user_id, task_name, task_note, interval_min):
    if not task_name or not str(task_name).strip():
        raise ValueError("task_name is empty")
    # interval может быть 0 для разовых, >0 для периодических
    interval_min = int(interval_min)

    conn = get_connection()
    cur = conn.cursor()
    next_ts = time.time() + (interval_min * 60 if interval_min > 0 else 0)  # если 0 — выставим позже вручную
    cur.execute("""
        INSERT INTO tasks (user_id, task_name, task_note, interval, status, next_reminder_at, paused_until, is_one_shot)
        VALUES (?, ?, ?, ?, 1, ?, NULL, ?)
    """, (user_id, task_name.strip(), task_note, interval_min, next_ts, 1 if interval_min == 0 else 0))
    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return task_id

def count_open(user_id) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 1", (user_id,))
    c = cur.fetchone()[0]
    conn.close()
    return c

def list_open_paged(user_id, offset, limit):
    if limit <= 0:
        return []
    if offset < 0:
        offset = 0
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, task_name, next_reminder_at, interval, task_note, paused_until, is_one_shot
        FROM tasks
        WHERE user_id = ? AND status = 1
        ORDER BY next_reminder_at ASC
        LIMIT ? OFFSET ?
    """, (user_id, int(limit), int(offset)))
    rows = cur.fetchall()
    conn.close()
    return rows

# «рандом по сидy» для /list
PRIME = 2147483647
def list_open_paged_random(user_id, offset, limit, a, b):
    if limit <= 0:
        return []
    if offset < 0:
        offset = 0
    conn = get_connection()
    cur = conn.cursor()
    # сортируем детерминированно по сидy
    cur.execute(f"""
        SELECT id, task_name, next_reminder_at, interval, task_note, paused_until, is_one_shot
        FROM tasks
        WHERE user_id = ? AND status = 1
        ORDER BY ((id * ?) + ?) % {PRIME} ASC
        LIMIT ? OFFSET ?
    """, (user_id, int(a), int(b), int(limit), int(offset)))
    rows = cur.fetchall()
    conn.close()
    return rows

def add_task_at(user_id: int, task_name: str, task_note: str | None, when_ts: float) -> int:
    if not task_name or not task_name.strip():
        raise ValueError("task_name is empty")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks (user_id, task_name, task_note, interval, status, next_reminder_at, paused_until, is_one_shot)
        VALUES (?, ?, ?, 0, 1, ?, NULL, 1)
    """, (user_id, task_name.strip(), task_note, float(when_ts)))
    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return task_id

def get_due(now_ts, limit, user_id=None):
    """задачи, где next_reminder_at <= now и (paused_until IS NULL или <= now)"""
    if limit <= 0:
        return []
    conn = get_connection()
    cur = conn.cursor()
    if user_id is not None:
        cur.execute("""
            SELECT id, user_id, task_name, task_note, status, next_reminder_at, interval, paused_until
            FROM tasks
            WHERE user_id = ?
              AND status = 1
              AND next_reminder_at <= ?
              AND (paused_until IS NULL OR paused_until <= ?)
            ORDER BY next_reminder_at ASC
            LIMIT ?
        """, (user_id, now_ts, now_ts, int(limit)))
    else:
        cur.execute("""
            SELECT id, user_id, task_name, task_note, status, next_reminder_at, interval, paused_until
            FROM tasks
            WHERE status = 1
              AND next_reminder_at <= ?
              AND (paused_until IS NULL OR paused_until <= ?)
            ORDER BY next_reminder_at ASC
            LIMIT ?
        """, (now_ts, now_ts, int(limit)))
    rows = cur.fetchall()
    conn.close()
    return rows

def reschedule(task_id, user_id, next_ts) -> bool:
    if next_ts <= time.time():
        return False
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE tasks
        SET next_reminder_at = ?, paused_until = NULL
        WHERE id = ? AND user_id = ?
    """, (next_ts, task_id, user_id))
    conn.commit()
    ok = (cur.rowcount == 1)
    conn.close()
    return ok

def snooze(task_id, user_id, minutes) -> bool:
    if minutes <= 0:
        return False
    conn = get_connection()
    cur = conn.cursor()
    # читаем текущее значение, чтобы продлевать от большего из(now, paused_until)
    cur.execute("SELECT paused_until FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    row = cur.fetchone()
    now = time.time()
    base = now
    if row and row["paused_until"]:
        try:
            base = max(now, float(row["paused_until"]))
        except Exception:
            base = now
    new_until = base + int(minutes) * 60
    cur.execute("UPDATE tasks SET paused_until = ? WHERE id = ? AND user_id = ?", (new_until, task_id, user_id))
    conn.commit()
    ok = (cur.rowcount == 1)
    conn.close()
    return ok

def mark_done(task_id, user_id) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status = 0 WHERE id = ? AND user_id = ?", (task_id, user_id))
    conn.commit()
    ok = (cur.rowcount == 1)
    conn.close()
    return ok

def delete_task(task_id, user_id) -> bool:
    # мягкое удаление = статус 0
    return mark_done(task_id, user_id)


def is_user_sleeping(user_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT is_sleeping FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row["is_sleeping"]) if row else False

def set_sleep_state(user_id: int, sleeping: bool):
    now = time.time()
    conn = get_connection()
    cur = conn.cursor()
    if sleeping:
        cur.execute("UPDATE users SET is_sleeping = 1, sleep_started_at = ? WHERE id = ?", (now, user_id))
    else:
        cur.execute("UPDATE users SET is_sleeping = 0 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_sleep_started_at(user_id: int) -> float | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT sleep_started_at FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row or row["sleep_started_at"] is None:
        return None
    try:
        return float(row["sleep_started_at"])
    except Exception:
        return None

def get_missed_during_sleep(user_id: int, since_ts: float | None, now_ts: float) -> list[sqlite3.Row]:
    conn = get_connection()
    cur = conn.cursor()
    if since_ts is not None:
        cur.execute("""
            SELECT id, user_id, task_name, task_note, next_reminder_at, interval, paused_until, is_one_shot
            FROM tasks
            WHERE user_id = ?
              AND status = 1
              AND next_reminder_at <= ?
              AND next_reminder_at >= ?
            ORDER BY next_reminder_at ASC
        """, (user_id, now_ts, since_ts))
    else:
        cur.execute("""
            SELECT id, user_id, task_name, task_note, next_reminder_at, interval, paused_until, is_one_shot
            FROM tasks
            WHERE user_id = ?
              AND status = 1
              AND next_reminder_at <= ?
            ORDER BY next_reminder_at ASC
        """, (user_id, now_ts))
    rows = cur.fetchall()
    conn.close()
    return rows
