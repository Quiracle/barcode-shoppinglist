from pathlib import Path

from app.data.db import Database, DEFAULT_LIST_ID
from app.data.repositories import ShoppingRepository
from app.domain.add_or_increment import add_or_increment_item
from app.domain.models import ScanDebouncer


def build_repo(tmp_path: Path) -> ShoppingRepository:
    db = Database(str(tmp_path / "test.db"))
    return ShoppingRepository(db)


def test_add_or_increment_increments_existing_unpurchased(tmp_path: Path) -> None:
    repo = build_repo(tmp_path)
    debouncer = ScanDebouncer(window_ms=0)

    first = add_or_increment_item(repo, debouncer, DEFAULT_LIST_ID, "12345678")
    second = add_or_increment_item(repo, debouncer, DEFAULT_LIST_ID, "12345678")

    assert first is not None
    assert second is not None
    assert first["id"] == second["id"]
    assert second["quantity"] == 2


def test_add_or_increment_does_not_increment_purchased_item(tmp_path: Path) -> None:
    repo = build_repo(tmp_path)
    debouncer = ScanDebouncer(window_ms=0)

    purchased = repo.create_item(
        list_id=DEFAULT_LIST_ID,
        name="Unknown item",
        barcode="55555555",
        purchased=1,
        quantity=1,
    )

    new_item = add_or_increment_item(repo, debouncer, DEFAULT_LIST_ID, "55555555")

    assert new_item is not None
    assert new_item["id"] != purchased["id"]
    assert new_item["purchased"] == 0
    assert new_item["quantity"] == 1


def test_add_or_increment_accepts_non_numeric_when_enabled(tmp_path: Path) -> None:
    repo = build_repo(tmp_path)
    debouncer = ScanDebouncer(window_ms=0)

    item = add_or_increment_item(
        repo,
        debouncer,
        DEFAULT_LIST_ID,
        "HELLO-QR-123",
        allowed_lengths=(12,),
        allow_non_numeric=True,
    )

    assert item is not None
    assert item["barcode"] == "HELLO-QR-123"
