"""Pure text -> catno parsing. See design doc §8.

Assumes the photo is a clean, close-up shot of just the catno (a user
framing choice, not something this function verifies) -- so parsing is
just whitespace/newline cleanup, not extraction from a noisy full-label
scan.
"""

from __future__ import annotations


def parse_catno(raw_text: str) -> str | None:
    collapsed = " ".join(raw_text.split())
    return collapsed if collapsed else None
