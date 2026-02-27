from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class ParsedScan:
    barcode: str


class BarcodeParser:
    def __init__(self, terminator: str = "KEY_ENTER") -> None:
        self.terminator = terminator
        self._buffer: list[str] = []

    def reset(self) -> None:
        self._buffer.clear()

    def feed_keycode(self, keycode: str) -> ParsedScan | None:
        if keycode == self.terminator:
            barcode = "".join(self._buffer).strip()
            self._buffer.clear()
            if not barcode:
                return None
            return ParsedScan(barcode=barcode)

        mapped = map_keycode_to_digit(keycode)
        if mapped is not None:
            self._buffer.append(mapped)
        return None


def map_keycode_to_digit(keycode: str) -> str | None:
    mapping = {
        "KEY_0": "0",
        "KEY_1": "1",
        "KEY_2": "2",
        "KEY_3": "3",
        "KEY_4": "4",
        "KEY_5": "5",
        "KEY_6": "6",
        "KEY_7": "7",
        "KEY_8": "8",
        "KEY_9": "9",
        "KEY_KP0": "0",
        "KEY_KP1": "1",
        "KEY_KP2": "2",
        "KEY_KP3": "3",
        "KEY_KP4": "4",
        "KEY_KP5": "5",
        "KEY_KP6": "6",
        "KEY_KP7": "7",
        "KEY_KP8": "8",
        "KEY_KP9": "9",
    }
    return mapping.get(keycode)
