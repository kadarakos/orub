"""Pure mapping from validated Discogs DTOs to domain catalog types.

See design doc §4.2. No I/O here -- everything in this module is a plain
function over already-validated pydantic data, which is what makes it
testable without a network connection.
"""

from __future__ import annotations

import attrs

from orub.discogs.models import (
    DiscogsArtistDTO,
    DiscogsFormatDTO,
    DiscogsReleaseDTO,
    DiscogsTrackDTO,
)
from orub.domain.catalog import Release, Track
from orub.domain.identity import ArtistId, LabelId, ReleaseId, TrackId, TrackPosition
from orub.domain.result import Err, Ok, Result
from orub.domain.sums import RecordFormat

_FORMAT_BY_DISCOGS_NAME = {
    "Vinyl": RecordFormat.VINYL,
    "CD": RecordFormat.CD,
    "Cassette": RecordFormat.CASSETTE,
    "File": RecordFormat.FILE,
    "Lathe Cut": RecordFormat.LATHE_CUT,
}


def _record_format(formats: list[DiscogsFormatDTO]) -> RecordFormat | None:
    if not formats:
        return None
    return _FORMAT_BY_DISCOGS_NAME.get(formats[0].name)


def _artist_ids(artists: list[DiscogsArtistDTO]) -> tuple[ArtistId, ...]:
    # Discogs sometimes credits the same artist twice on one release/track,
    # e.g. a Latin-script name and a transliteration joined by "=" on
    # Japanese-market releases -- both entries carry the same id. Dedupe
    # (order-preserving) so persistence doesn't violate the (release,
    # track, artist) unique constraint on track_artist_ids.
    return tuple(dict.fromkeys(ArtistId(a.id) for a in artists))


def _track_from_dto(
    dto: DiscogsTrackDTO, release_id: ReleaseId, release_artist_ids: tuple[ArtistId, ...]
) -> Track | None:
    if dto.type != "track" or not dto.position:
        return None
    artist_ids = _artist_ids(dto.artists) if dto.artists else release_artist_ids
    return Track(
        id=TrackId(release_id=release_id, position=TrackPosition(dto.position)),
        title=dto.title,
        artist_ids=artist_ids,
    )


def release_from_dto(dto: DiscogsReleaseDTO) -> Result[Release, str]:
    record_format = _record_format(dto.formats)
    if record_format is None:
        formats = [f.name for f in dto.formats]
        return Err(f"release {dto.id}: no supported RecordFormat in {formats!r}")

    if not dto.labels:
        return Err(f"release {dto.id}: has no label")

    release_id = ReleaseId(dto.id)
    release_artist_ids = _artist_ids(dto.artists)
    tracklist = tuple(
        track
        for raw_track in dto.tracklist
        if (track := _track_from_dto(raw_track, release_id, release_artist_ids)) is not None
    )

    return Ok(
        Release(
            id=release_id,
            title=dto.title,
            label_id=LabelId(dto.labels[0].id),
            year=dto.year,
            format=record_format,
            tracklist=tracklist,
            catno=dto.labels[0].catno,
        )
    )


@attrs.frozen(slots=True)
class DiscogsTagHints:
    """Discogs-supplied categorical vocabulary for a release, grouped the
    way it'll be surfaced as tags -- one tuple per reserved tag category
    (genre/style/format). Not part of `Release` itself: these become
    `Tag` rows via a get-or-create step at persistence time, not domain
    catalog fields.
    """

    genres: tuple[str, ...] = ()
    styles: tuple[str, ...] = ()
    format_descriptions: tuple[str, ...] = ()


def tag_hints_from_dto(dto: DiscogsReleaseDTO) -> DiscogsTagHints:
    return DiscogsTagHints(
        genres=tuple(dto.genres),
        styles=tuple(dto.styles),
        format_descriptions=tuple(
            description for fmt in dto.formats for description in fmt.descriptions
        ),
    )
