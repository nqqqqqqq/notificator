# app/db/repo.py
import sqlite3
import time
from pathlib import Path

# ---- подключение к БД (абсолютный путь рядом с этим файлом) ----
DB_PATH = Path(__file__).with_name("database.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---- users ----
def get_or_create_user(telegram_user_id, username=None):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE telegram_user_id = ?", (telegram_user_id,))
    user = cur.fetchone()
    if user:
        conn.close()
        return user

    cur.execute(
        "INSERT INTO users (telegram_user_id, username) VALUES (?, ?)",
        (telegram_user_id, username)
    )
    conn.commit()

    cur.execute("SELECT * FROM users WHERE telegram_user_id = ?", (telegram_user_id,))
    user = cur.fetchone()

    conn.close()
    return user


def update_timezone(user_id, tz) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET timezone = ? WHERE id = ?", (tz, user_id))
    conn.commit()
    ok = (cur.rowcount == 1)
    conn.close()
    return ok


# ---- tasks ----
# status: 1 = активна, 0 = выполнена/архив
def add_task(user_id, task_name, task_note, interval_min):
    if not task_name or not str(task_name).strip():
        raise ValueError("task_name is empty")
    # if interval_min <= 0:
    #     raise ValueError("interval must be > 0")

    conn = get_connection()
    cur = conn.cursor()

    next_reminder_at = time.time() + int(interval_min) * 60
    status = 1
    paused_until = None

    cur.execute("""
        INSERT INTO tasks (user_id, task_name, task_note, interval, status, next_reminder_at, paused_until)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, task_name.strip(), task_note, interval_min, status, next_reminder_at, paused_until))

    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return task_id


def list_open(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, task_name, task_note, status, next_reminder_at, interval, paused_until
        FROM tasks
        WHERE user_id = ? AND status = 1
        ORDER BY next_reminder_at ASC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_due(now_ts, limit, user_id=None):
    """Задачи, срок которых наступил: next_reminder_at <= now и (paused_until IS NULL или <= now)."""
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


def mark_done(task_id, user_id) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status = 0 WHERE id = ? AND user_id = ?", (task_id, user_id))
    conn.commit()
    ok = (cur.rowcount == 1)
    conn.close()
    return ok


def snooze(task_id, user_id, minutes) -> bool:
    if minutes <= 0:
        return False
    conn = get_connection()
    cur = conn.cursor()
    paused_until_time = time.time() + int(minutes) * 60
    cur.execute(
        "UPDATE tasks SET paused_until = ? WHERE id = ? AND user_id = ?",
        (paused_until_time, task_id, user_id)
    )
    conn.commit()
    ok = (cur.rowcount == 1)
    conn.close()
    return ok


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


def set_interval(task_id, user_id, minutes) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE tasks
        SET interval = ?
        WHERE id = ? AND user_id = ?
    """, (int(minutes), task_id, user_id))
    conn.commit()
    ok = (cur.rowcount == 1)
    conn.close()
    return ok


def delete_task(task_id, user_id) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status = 0 WHERE id = ? AND user_id = ?", (task_id, user_id))
    conn.commit()
    ok = (cur.rowcount == 1)
    conn.close()
    return ok


def count_open(user_id) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 1", (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count


def list_open_paged(user_id, offset, limit):
    if limit <= 0:
        return []
    if offset < 0:
        offset = 0

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, task_name, next_reminder_at, interval, task_note, paused_until
        FROM tasks
        WHERE user_id = ? AND status = 1
        ORDER BY next_reminder_at ASC
        LIMIT ? OFFSET ?
    """, (user_id, int(limit), int(offset)))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_user_by_id(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row