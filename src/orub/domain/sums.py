"""Closed sum types and small value types. See design doc §3 Closed sum types.

Fixed sets of variants are Enums, never bare strings, so `match` statements
over them can be exhaustive and pyright --strict can catch missing cases.
"""

from __future__ import annotations

from enum import Enum

import attrs


class EdgeSource(Enum):
    """Where a track-follows-track Edge came from."""

    AUTO = "auto"
    MANUAL = "manual"


class RecordFormat(Enum):
    """Physical/digital format of a Release, as reported by Discogs.

    Grow this set as ingestion work (§8) discovers which format strings
    Discogs actually returns; unrecognized formats should fail validation
    at the boundary rather than being silently coerced into a catch-all.
    """

    VINYL = "Vinyl"
    CD = "CD"
    CASSETTE = "Cassette"
    FILE = "File"
    LATHE_CUT = "Lathe Cut"


class Condition(Enum):
    """Discogs' standard media grading scale, for CollectionItem.condition.

    Not explicitly named as a closed sum type in design doc §3, but it's a
    fixed vocabulary the same way RecordFormat is -- flag for confirmation.
    """

    MINT = "Mint (M)"
    NEAR_MINT = "Near Mint (NM or M-)"
    VERY_GOOD_PLUS = "Very Good Plus (VG+)"
    VERY_GOOD = "Very Good (VG)"
    GOOD_PLUS = "Good Plus (G+)"
    GOOD = "Good (G)"
    FAIR = "Fair (F)"
    POOR = "Poor (P)"


class MusicalKey(Enum):
    """A key in Camelot wheel notation, for harmonic-mixing compatibility."""

    CAMELOT_1A = "1A"
    CAMELOT_2A = "2A"
    CAMELOT_3A = "3A"
    CAMELOT_4A = "4A"
    CAMELOT_5A = "5A"
    CAMELOT_6A = "6A"
    CAMELOT_7A = "7A"
    CAMELOT_8A = "8A"
    CAMELOT_9A = "9A"
    CAMELOT_10A = "10A"
    CAMELOT_11A = "11A"
    CAMELOT_12A = "12A"
    CAMELOT_1B = "1B"
    CAMELOT_2B = "2B"
    CAMELOT_3B = "3B"
    CAMELOT_4B = "4B"
    CAMELOT_5B = "5B"
    CAMELOT_6B = "6B"
    CAMELOT_7B = "7B"
    CAMELOT_8B = "8B"
    CAMELOT_9B = "9B"
    CAMELOT_10B = "10B"
    CAMELOT_11B = "11B"
    CAMELOT_12B = "12B"


@attrs.frozen(slots=True)
class Bpm:
    value: float
