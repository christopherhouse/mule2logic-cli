"""ANSI color and spinner helpers for CLI output."""

from __future__ import annotations

import sys
import threading
import time


# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------

def cyan(s: str) -> str:
    return f"\x1b[36m{s}\x1b[0m"

def green(s: str) -> str:
    return f"\x1b[32m{s}\x1b[0m"

def yellow(s: str) -> str:
    return f"\x1b[33m{s}\x1b[0m"

def red(s: str) -> str:
    return f"\x1b[31m{s}\x1b[0m"

def dim(s: str) -> str:
    return f"\x1b[2m{s}\x1b[0m"

def bold(s: str) -> str:
    return f"\x1b[1m{s}\x1b[0m"


# ---------------------------------------------------------------------------
# Spinner
# ---------------------------------------------------------------------------

_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

_active_spinners: list[Spinner] = []


class Spinner:
    """A simple terminal spinner that runs in a background thread."""

    def __init__(self, message: str) -> None:
        self._message = message
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        _active_spinners.append(self)
        self._thread.start()

    def _spin(self) -> None:
        idx = 0
        while not self._stop_event.is_set():
            frame = cyan(_FRAMES[idx % len(_FRAMES)])
            sys.stderr.write(f"\r{frame} {self._message}")
            sys.stderr.flush()
            idx += 1
            time.sleep(0.08)

    def stop(self, final_msg: str) -> None:
        self._stop_event.set()
        self._thread.join(timeout=1.0)
        if self in _active_spinners:
            _active_spinners.remove(self)
        sys.stderr.write(f"\r{final_msg}\n")
        sys.stderr.flush()


def stop_all_spinners() -> None:
    """Force-stop every active spinner (used on fatal errors)."""
    for s in _active_spinners[:]:
        s._stop_event.set()
        s._thread.join(timeout=0.5)
    _active_spinners.clear()
