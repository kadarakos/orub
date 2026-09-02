"""Gateway-level errors for the OCR extraction step. See design doc §8.

Mirrors `orub.discogs.errors.FetchError`: an invalid/corrupt upload is an
expected failure (the user's camera or file picker can hand us garbage),
not a programmer error, so it's modeled as a Result rather than raised.
"""

from __future__ import annotations

import attrs


@attrs.frozen(slots=True)
class InvalidImage:
    message: str


type OcrError = InvalidImage
