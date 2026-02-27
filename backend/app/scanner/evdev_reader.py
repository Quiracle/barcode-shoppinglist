from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from app.scanner.barcode_parser import BarcodeParser

logger = logging.getLogger(__name__)

try:
    from evdev import InputDevice, categorize, ecodes, list_devices
except Exception:  # pragma: no cover - evdev not available in some test envs
    InputDevice = None
    categorize = None
    ecodes = None
    list_devices = None


@dataclass
class ScannerConfig:
    scanner_device: Optional[str]
    scanner_name: Optional[str]
    terminator_key: str = "KEY_ENTER"
    discovery_retry_seconds: int = 5


class EvdevScannerReader:
    def __init__(self, config: ScannerConfig, on_scan: Callable[[str], None]) -> None:
        self.config = config
        self.on_scan = on_scan
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        if InputDevice is None:
            logger.warning("python-evdev is unavailable; scanner reader disabled")
            return

        parser = BarcodeParser(terminator=self.config.terminator_key)

        while not self._stop_event.is_set():
            device = self._discover_device()
            if device is None:
                logger.warning("Scanner device not found; retrying in %ss", self.config.discovery_retry_seconds)
                time.sleep(self.config.discovery_retry_seconds)
                continue

            logger.info("Scanner connected: %s (%s)", device.path, device.name)
            try:
                for event in device.read_loop():
                    if self._stop_event.is_set():
                        break
                    if event.type != ecodes.EV_KEY:
                        continue
                    key_event = categorize(event)
                    if key_event.keystate != key_event.key_down:
                        continue

                    keycode = key_event.keycode
                    if isinstance(keycode, list):
                        keycode = keycode[0]

                    parsed = parser.feed_keycode(str(keycode))
                    if parsed is not None:
                        self.on_scan(parsed.barcode)
            except OSError as exc:
                logger.warning("Lost scanner device (%s). Retrying discovery.", exc)
                time.sleep(self.config.discovery_retry_seconds)
            except Exception:
                logger.exception("Unhandled scanner reader error")
                time.sleep(self.config.discovery_retry_seconds)

    def _discover_device(self):
        explicit = self.config.scanner_device
        if explicit:
            try:
                return InputDevice(explicit)
            except Exception:
                logger.warning("Configured scanner device %s is not accessible", explicit)

        if list_devices is None:
            return None

        desired_name = (self.config.scanner_name or "").lower().strip()
        for path in list_devices():
            try:
                device = InputDevice(path)
            except Exception:
                continue

            name = (device.name or "").lower()
            if desired_name and desired_name in name:
                return device

            if not desired_name and "barcode" in name:
                return device

        return None


def scanner_config_from_env() -> ScannerConfig:
    return ScannerConfig(
        scanner_device=os.getenv("SCANNER_DEVICE"),
        scanner_name=os.getenv("SCANNER_NAME"),
        terminator_key=os.getenv("SCANNER_TERMINATOR", "KEY_ENTER"),
        discovery_retry_seconds=int(os.getenv("SCANNER_RETRY_SECONDS", "5")),
    )
