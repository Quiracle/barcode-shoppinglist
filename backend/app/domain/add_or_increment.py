from __future__ import annotations

from typing import Optional

from app.data.repositories import ShoppingRepository
from app.domain.models import ScanDebouncer

UNKNOWN_ITEM_NAME = "Unknown item"


def normalize_barcode(barcode: str) -> Optional[str]:
    cleaned = barcode.strip()
    if not cleaned:
        return None
    return cleaned


def barcode_is_valid(barcode: str, allowed_lengths: tuple[int, ...]) -> bool:
    if not barcode.isdigit():
        return False
    return len(barcode) in allowed_lengths


def add_or_increment_item(
    repository: ShoppingRepository,
    debouncer: ScanDebouncer,
    list_id: str,
    barcode: str,
    allowed_lengths: tuple[int, ...] = (8, 12, 13, 14),
) -> Optional[dict]:
    normalized = normalize_barcode(barcode)
    if normalized is None:
        return None

    if not barcode_is_valid(normalized, allowed_lengths):
        return None

    decision = debouncer.should_accept(normalized)
    if not decision.accepted:
        return None

    existing = repository.find_unpurchased_by_barcode(list_id, normalized)
    if existing is not None:
        return repository.increment_item(existing["id"])

    return repository.create_item(
        list_id=list_id,
        name=UNKNOWN_ITEM_NAME,
        quantity=1,
        barcode=normalized,
        purchased=0,
    )
