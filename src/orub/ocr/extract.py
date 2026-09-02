"""Impure OCR edge: image bytes -> raw text via tesseract. See design doc §8.

Kept separate from `parse.py`'s pure text -> catno logic, same pure-core/
impure-edge split as `orub.discogs.client`/`orub.discogs.mapping`.
"""

from __future__ import annotations

import io
from typing import cast

import pytesseract  # pyright: ignore[reportMissingTypeStubs]
from PIL import Image, UnidentifiedImageError

from orub.domain.result import Err, Ok, Result
from orub.ocr.errors import InvalidImage, OcrError


def run_ocr(image_bytes: bytes) -> Result[str, OcrError]:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except (UnidentifiedImageError, OSError) as error:
        return Err(InvalidImage(str(error)))
    # Default output_type=Output.STRING guarantees a str at runtime; the
    # pytesseract stub just can't express that as a narrower return type.
    text = cast(str, pytesseract.image_to_string(image))  # pyright: ignore[reportUnknownMemberType]
    return Ok(text)
