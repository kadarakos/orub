"""Catalog entities (not user-specific). See design doc §3 Catalog entities.

Label and Artist are referenced by id rather than embedded, since they're
shared across many releases/tracks; Track is embedded in its Release's
tracklist, since a track doesn't exist independently of the release it
came from. This is a judgment call the design doc left open -- revisit if
the ingestion/persistence layers (§8) want it the other way.
"""

from __future__ import annotations

import attrs

from orub.domain.identity import ArtistId, LabelId, ReleaseId, TrackId
from orub.domain.sums import Bpm, MusicalKey, RecordFormat


@attrs.frozen(slots=True)
class Artist:
    id: ArtistId
    name: str


@attrs.frozen(slots=True)
class Label:
    id: LabelId
    name: str


@attrs.frozen(slots=True)
class Track:
    id: TrackId
    title: str
    artist_ids: tuple[ArtistId, ...]
    bpm: Bpm | None = None
    key: MusicalKey | None = None


@attrs.frozen(slots=True)
class Release:
    id: ReleaseId
    title: str
    label_id: LabelId
    year: int | None
    format: RecordFormat
    tracklist: tuple[Track, ...]
    catno: str | None = None
