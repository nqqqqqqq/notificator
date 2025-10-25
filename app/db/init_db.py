import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

creation_tasks = """CREATE TABLE IF NOT EXISTS tasks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_name TEXT NOT NULL,
                task_note TEXT,
                status INTEGER NOT NULL DEFAULT 0 CHECK (status IN (0,1)),
                remind_time REAL NOT NULL,
                interval_minutes REAL NOT NULL,
                snooze_until REAL
                    )"""

cursor.execute(creation_tasks)

creation_users = """CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER UNIQUE NOT NULL,
                username TEXT NOT NULL,
                timezone TEXT DEFAULT 'Europe/Warsaw',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )"""


cursor.execute(creation_users)


print("Database created successfully")
conn.commit()
conn.close()
