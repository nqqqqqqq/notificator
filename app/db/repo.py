# repo.py
import sqlite3
import time


# --- подключение к БД ---
def get_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


# --- users ---
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


def update_timezone(user_id, tz):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET timezone = ? WHERE id = ?", (tz, user_id))
    conn.commit()
    conn.close()
    return user_id


# --- tasks ---
# status: 1 = активна, 0 = выполнена
def add_task(user_id, task_name, task_notes, interval_min):
    conn = get_connection()
    cur = conn.cursor()

    remind_time = time.time() + interval_min * 60
    status = 1
    snooze_until = None

    cur.execute("""
        INSERT INTO tasks (user_id, task_name, task_notes, interval_minutes, status, remind_time, snooze_until)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, task_name, task_notes, interval_min, status, remind_time, snooze_until))

    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return task_id


def list_open(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, task_name, task_notes, status, remind_time, interval_minutes, snooze_until
        FROM tasks
        WHERE user_id = ? AND status = 1
        ORDER BY remind_time ASC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_due(now_ts, limit, user_id=None):
    conn = get_connection()
    cur = conn.cursor()
    if user_id is not None:
        cur.execute("""
            SELECT ...
            FROM tasks
            WHERE user_id = ?
              AND status = 1
              AND remind_time <= ?
              AND (snooze_until IS NULL OR snooze_until <= ?)
            ORDER BY remind_time ASC
            LIMIT ?
        """, (user_id, now_ts, now_ts, limit))
    else:
        cur.execute("""
            SELECT ...
            FROM tasks
            WHERE status = 1
              AND remind_time <= ?
              AND (snooze_until IS NULL OR snooze_until <= ?)
            ORDER BY remind_time ASC
            LIMIT ?
        """, (now_ts, now_ts, limit))
    rows = cur.fetchall()
    conn.close()
    return rows

def mark_done(task_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status = 0 WHERE id = ? AND user_id = ?", (task_id, user_id))
    conn.commit()
    conn.close()
    return cur.rowcount == 1


def snooze(task_id, user_id, minutes) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    if minutes <= 0:
        conn.close()
        return False
    snooze_until_time = time.time() + minutes * 60
    cur.execute("UPDATE tasks SET snooze_until = ? WHERE id = ? AND user_id = ?", (snooze_until_time, task_id, user_id))
    conn.commit()
    conn.close()
    return cur.rowcount == 1


def reschedule(task_id, user_id, next_ts):
    conn = get_connection()
    cur = conn.cursor()
    if next_ts <= time.time():
        conn.close()
        return False
    cur.execute("""
        UPDATE tasks
        SET remind_time = ?, snooze_until = NULL
        WHERE id = ? AND user_id = ?
    """, (next_ts, task_id, user_id))
    conn.commit()
    conn.close()
    return cur.rowcount == 1


def set_interval(task_id, user_id, minutes):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE tasks
        SET interval_minutes = ?
        WHERE id = ? AND user_id = ?
    """, (minutes, task_id, user_id))
    conn.commit()
    conn.close()
    return cur.rowcount == 1

def delete_task(task_id, user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("UPDATE tasks SET status = 0 WHERE id = ? AND user_id = ?", (task_id, user_id))

    conn.commit()
    conn.close()
    return cur.rowcount == 1

def count_open(user_id) -> int:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 1", (user_id,))

    count  = cur.fetchone()[0]
    conn.close()
    return count

def list_open_paged(user_id, offset, limit):
    conn = get_connection()
    cur = conn.cursor()
    if limit <= 0:
        conn.close()
        return []
    if offset <= 0:
        offset = 0

    cur.execute("SELECT id, task_name, remind_time, interval_minutes, task_notes, snooze_until FROM tasks WHERE user_id = ? AND status = 1 ORDER BY remind_time LIMIT ? OFFSET ?", (user_id, limit, offset))

    rows = cur.fetchall()
    conn.close()
    return rows

