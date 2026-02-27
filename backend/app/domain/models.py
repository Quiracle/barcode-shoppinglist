from dataclasses import dataclass
from threading import Lock
from time import time
from typing import Optional


@dataclass
class ScanDecision:
    accepted: bool
    reason: Optional[str] = None


class ScanDebouncer:
    def __init__(self, window_ms: int = 800) -> None:
        self.window_ms = window_ms
        self.last_scan_barcode: Optional[str] = None
        self.last_scan_at: int = 0
        self._lock = Lock()

    def should_accept(self, barcode: str) -> ScanDecision:
        now = int(time() * 1000)
        with self._lock:
            if (
                self.last_scan_barcode == barcode
                and (now - self.last_scan_at) < self.window_ms
            ):
                return ScanDecision(accepted=False, reason="duplicate_within_window")
            self.last_scan_barcode = barcode
            self.last_scan_at = now
            return ScanDecision(accepted=True)
