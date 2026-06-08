from __future__ import annotations
from datetime import datetime, timezone
from .db import connect


class History:
    def __init__(self, db_path: str):
        self._conn = connect(db_path)

    def last_status(self, number: str) -> str | None:
        row = self._conn.execute(
            "SELECT status FROM history WHERE number=? ORDER BY id DESC LIMIT 1",
            (number,)).fetchone()
        return row[0] if row else None

    def record(self, number: str, status: str) -> bool:
        """Append if changed. Returns True when status changed."""
        previous = self.last_status(number)
        if previous == status:
            return False
        self._conn.execute(
            "INSERT INTO history(number, status, changed_at) VALUES (?,?,?)",
            (number, status, datetime.now(timezone.utc).isoformat()))
        self._conn.commit()
        return True
