from __future__ import annotations
import sqlite3
from pathlib import Path


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS cache(
        number TEXT PRIMARY KEY, payload TEXT, fetched_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS history(
        id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT,
        status TEXT, changed_at TEXT)""")
    conn.commit()
    return conn
