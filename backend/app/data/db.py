import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_LIST_ID = "default"
DEFAULT_LIST_NAME = "My Shopping List"


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure_parent()
        self._initialize_schema()
        self.ensure_default_list()

    def _ensure_parent(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def connection(self) -> sqlite3.Connection:
        return self._connect()

    def _initialize_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        schema_sql = schema_path.read_text(encoding="utf-8")
        conn = self._connect()
        try:
            conn.executescript(schema_sql)
            conn.commit()
        finally:
            conn.close()

    def ensure_default_list(self) -> None:
        from time import time

        now = int(time() * 1000)
        conn = self._connect()
        try:
            existing = conn.execute(
                "SELECT id FROM lists WHERE id = ? LIMIT 1", (DEFAULT_LIST_ID,)
            ).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO lists (id, name, createdAt, updatedAt) VALUES (?, ?, ?, ?)",
                    (DEFAULT_LIST_ID, DEFAULT_LIST_NAME, now, now),
                )
                conn.commit()
        finally:
            conn.close()
