from app.scanner.barcode_parser import BarcodeParser


def test_barcode_parser_collects_digits_until_enter() -> None:
    parser = BarcodeParser()
    assert parser.feed_keycode("KEY_1") is None
    assert parser.feed_keycode("KEY_2") is None
    parsed = parser.feed_keycode("KEY_ENTER")

    assert parsed is not None
    assert parsed.barcode == "12"
