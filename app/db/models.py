import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

creation_table = """CREATE TABLE tasks(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    task_notes TEXT NOT NULL,
                    status TEXT NOT NULL,
                    next_reminder_at REAL NOT NULL
                    )"""

cursor.execute(creation_table)

print("Database created successfully")
conn.commit()
conn.close()
