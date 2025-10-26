# init_db.py
import sqlite3
from pathlib import Path

# База лежит рядом с этим файлом, чтобы и бот и инициализация открывали один и тот же файл
DB_PATH = Path(__file__).with_name("database.db")

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Включим внешние ключи на всякий
    cur.execute("PRAGMA foreign_keys = ON;")

    # ---- USERS ----
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_user_id  INTEGER NOT NULL UNIQUE,
        username          TEXT,                                -- может быть NULL
        timezone          TEXT DEFAULT 'Europe/Warsaw',
        created_at        TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at        TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # ---- TASKS ----
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id          INTEGER NOT NULL,
        task_name        TEXT NOT NULL,
        task_note       TEXT,                                 
        status           INTEGER NOT NULL DEFAULT 1 CHECK (status IN (0,1)),  -- 1=активна, 0=выполнена/архив
        remind_time      REAL    NOT NULL,                      -- time.time() (UTC, секунды)
        interval_minutes INTEGER NOT NULL,                      -- минуты
        snooze_until     REAL,                                  -- time.time() или NULL
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Индексы для скорости /list и get_due
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_tasks_status_user_time
    ON tasks(status, user_id, remind_time);
    """)

    print(f"Database created/updated at: {DB_PATH}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
