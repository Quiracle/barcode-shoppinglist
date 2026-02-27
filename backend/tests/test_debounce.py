from app.domain.models import ScanDebouncer


def test_debouncer_rejects_same_barcode_within_window() -> None:
    debouncer = ScanDebouncer(window_ms=999999)

    accepted = debouncer.should_accept("12345678")
    rejected = debouncer.should_accept("12345678")

    assert accepted.accepted is True
    assert rejected.accepted is False
