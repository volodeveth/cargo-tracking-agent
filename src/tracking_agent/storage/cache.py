from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from .db import connect


class Cache:
    def __init__(self, db_path: str, ttl_minutes: int):
        self._conn = connect(db_path)
        self._ttl = timedelta(minutes=ttl_minutes)

    def set(self, number: str, payload: dict) -> None:
        self._conn.execute(
            "REPLACE INTO cache(number, payload, fetched_at) VALUES (?,?,?)",
            (number, json.dumps(payload), datetime.now(timezone.utc).isoformat()))
        self._conn.commit()

    def get(self, number: str) -> dict | None:
        row = self._conn.execute(
            "SELECT payload, fetched_at FROM cache WHERE number=?", (number,)).fetchone()
        if not row:
            return None
        fetched = datetime.fromisoformat(row[1])
        if datetime.now(timezone.utc) - fetched >= self._ttl:
            return None
        return json.loads(row[0])
