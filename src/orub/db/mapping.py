"""Explicit mapping between `orub.db.models` rows and `orub.domain.catalog`
types. See design doc §4.3: the ORM is a separate representation, never
imported by domain/business logic -- everything crosses that boundary
through the pure functions here.
"""

from __future__ import annotations

from orub.db.models import ReleaseRow, TrackArtistRow, TrackRow
from orub.domain.catalog import Release, Track
from orub.domain.identity import ArtistId, LabelId, ReleaseId, TrackId, TrackPosition
from orub.domain.sums import Bpm, MusicalKey, RecordFormat


def _track_to_row(track: Track) -> TrackRow:
    return TrackRow(
        position=track.id.position.value,
        title=track.title,
        bpm=track.bpm.value if track.bpm is not None else None,
        key=track.key.value if track.key is not None else None,
        artist_ids=[TrackArtistRow(artist_id=artist_id.value) for artist_id in track.artist_ids],
    )


def _track_from_row(row: TrackRow, release_id: ReleaseId) -> Track:
    return Track(
        id=TrackId(release_id=release_id, position=TrackPosition(row.position)),
        title=row.title,
        artist_ids=tuple(ArtistId(a.artist_id) for a in row.artist_ids),
        bpm=Bpm(row.bpm) if row.bpm is not None else None,
        key=MusicalKey(row.key) if row.key is not None else None,
    )


def release_to_row(release: Release) -> ReleaseRow:
    return ReleaseRow(
        id=release.id.value,
        title=release.title,
        label_id=release.label_id.value,
        year=release.year,
        format=release.format.value,
        tracks=[_track_to_row(track) for track in release.tracklist],
    )


def release_from_row(row: ReleaseRow) -> Release:
    release_id = ReleaseId(row.id)
    return Release(
        id=release_id,
        title=row.title,
        label_id=LabelId(row.label_id),
        year=row.year,
        format=RecordFormat(row.format),
        tracklist=tuple(_track_from_row(track, release_id) for track in row.tracks),
    )
