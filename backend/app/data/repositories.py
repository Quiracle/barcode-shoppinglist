from __future__ import annotations

import uuid
from dataclasses import dataclass
from time import time
from typing import Any, Optional


@dataclass
class ListRecord:
    id: str
    name: str
    createdAt: int
    updatedAt: int


@dataclass
class ItemRecord:
    id: str
    listId: str
    barcode: Optional[str]
    name: str
    brand: Optional[str]
    imageUrl: Optional[str]
    quantity: int
    purchased: int
    userEditedName: int
    createdAt: int
    updatedAt: int
    lastAddedAt: int


def now_ms() -> int:
    return int(time() * 1000)


def row_to_dict(row: Any) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


class ShoppingRepository:
    def __init__(self, db) -> None:
        self.db = db

    def list_lists(self) -> list[dict[str, Any]]:
        conn = self.db.connection()
        try:
            rows = conn.execute(
                "SELECT id, name, createdAt, updatedAt FROM lists ORDER BY createdAt ASC"
            ).fetchall()
            return [row_to_dict(row) for row in rows]
        finally:
            conn.close()

    def create_list(self, name: str) -> dict[str, Any]:
        list_id = str(uuid.uuid4())
        now = now_ms()
        conn = self.db.connection()
        try:
            conn.execute(
                "INSERT INTO lists (id, name, createdAt, updatedAt) VALUES (?, ?, ?, ?)",
                (list_id, name, now, now),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, name, createdAt, updatedAt FROM lists WHERE id = ?",
                (list_id,),
            ).fetchone()
            return row_to_dict(row)
        finally:
            conn.close()

    def get_list(self, list_id: str) -> Optional[dict[str, Any]]:
        conn = self.db.connection()
        try:
            row = conn.execute(
                "SELECT id, name, createdAt, updatedAt FROM lists WHERE id = ? LIMIT 1",
                (list_id,),
            ).fetchone()
            return row_to_dict(row) if row else None
        finally:
            conn.close()

    def get_items(self, list_id: str) -> list[dict[str, Any]]:
        conn = self.db.connection()
        try:
            rows = conn.execute(
                """
                SELECT id, listId, barcode, name, brand, imageUrl, quantity, purchased,
                       userEditedName, createdAt, updatedAt, lastAddedAt
                FROM items
                WHERE listId = ?
                ORDER BY createdAt ASC
                """,
                (list_id,),
            ).fetchall()
            return [row_to_dict(row) for row in rows]
        finally:
            conn.close()

    def get_item_by_id(self, item_id: str) -> Optional[dict[str, Any]]:
        conn = self.db.connection()
        try:
            row = conn.execute(
                """
                SELECT id, listId, barcode, name, brand, imageUrl, quantity, purchased,
                       userEditedName, createdAt, updatedAt, lastAddedAt
                FROM items
                WHERE id = ?
                LIMIT 1
                """,
                (item_id,),
            ).fetchone()
            return row_to_dict(row) if row else None
        finally:
            conn.close()

    def find_unpurchased_by_barcode(self, list_id: str, barcode: str) -> Optional[dict[str, Any]]:
        conn = self.db.connection()
        try:
            row = conn.execute(
                """
                SELECT id, listId, barcode, name, brand, imageUrl, quantity, purchased,
                       userEditedName, createdAt, updatedAt, lastAddedAt
                FROM items
                WHERE listId = ? AND barcode = ? AND purchased = 0
                LIMIT 1
                """,
                (list_id, barcode),
            ).fetchone()
            return row_to_dict(row) if row else None
        finally:
            conn.close()

    def increment_item(self, item_id: str) -> dict[str, Any]:
        now = now_ms()
        conn = self.db.connection()
        try:
            conn.execute(
                """
                UPDATE items
                SET quantity = quantity + 1, updatedAt = ?, lastAddedAt = ?
                WHERE id = ?
                """,
                (now, now, item_id),
            )
            conn.commit()
            row = conn.execute(
                """
                SELECT id, listId, barcode, name, brand, imageUrl, quantity, purchased,
                       userEditedName, createdAt, updatedAt, lastAddedAt
                FROM items
                WHERE id = ?
                """,
                (item_id,),
            ).fetchone()
            return row_to_dict(row)
        finally:
            conn.close()

    def create_item(
        self,
        list_id: str,
        name: str,
        quantity: int = 1,
        barcode: Optional[str] = None,
        purchased: int = 0,
        brand: Optional[str] = None,
        image_url: Optional[str] = None,
        user_edited_name: int = 0,
    ) -> dict[str, Any]:
        item_id = str(uuid.uuid4())
        now = now_ms()
        conn = self.db.connection()
        try:
            conn.execute(
                """
                INSERT INTO items (
                    id, listId, barcode, name, brand, imageUrl, quantity, purchased,
                    userEditedName, createdAt, updatedAt, lastAddedAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    list_id,
                    barcode,
                    name,
                    brand,
                    image_url,
                    max(1, quantity),
                    purchased,
                    user_edited_name,
                    now,
                    now,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                """
                SELECT id, listId, barcode, name, brand, imageUrl, quantity, purchased,
                       userEditedName, createdAt, updatedAt, lastAddedAt
                FROM items
                WHERE id = ?
                """,
                (item_id,),
            ).fetchone()
            return row_to_dict(row)
        finally:
            conn.close()

    def update_item(self, item_id: str, **fields: Any) -> Optional[dict[str, Any]]:
        if not fields:
            return self.get_item_by_id(item_id)

        allowed = {"name", "quantity", "purchased", "brand", "imageUrl", "userEditedName"}
        assignments = []
        params = []

        for key, value in fields.items():
            if key not in allowed:
                continue
            assignments.append(f"{key} = ?")
            if key == "quantity":
                params.append(max(1, int(value)))
            elif key in {"purchased", "userEditedName"}:
                params.append(1 if value else 0)
            else:
                params.append(value)

        if not assignments:
            return self.get_item_by_id(item_id)

        assignments.append("updatedAt = ?")
        params.append(now_ms())
        params.append(item_id)

        conn = self.db.connection()
        try:
            conn.execute(
                f"UPDATE items SET {', '.join(assignments)} WHERE id = ?",
                tuple(params),
            )
            conn.commit()
            row = conn.execute(
                """
                SELECT id, listId, barcode, name, brand, imageUrl, quantity, purchased,
                       userEditedName, createdAt, updatedAt, lastAddedAt
                FROM items WHERE id = ?
                """,
                (item_id,),
            ).fetchone()
            return row_to_dict(row) if row else None
        finally:
            conn.close()

    def delete_item(self, item_id: str) -> Optional[dict[str, Any]]:
        existing = self.get_item_by_id(item_id)
        if existing is None:
            return None
        conn = self.db.connection()
        try:
            conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
            conn.commit()
            return existing
        finally:
            conn.close()
