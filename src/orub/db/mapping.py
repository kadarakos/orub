"""Explicit mapping between `orub.db.models` rows and `orub.domain.catalog`
types. See design doc §4.3: the ORM is a separate representation, never
imported by domain/business logic -- everything crosses that boundary
through the pure functions here.
"""

from __future__ import annotations

from datetime import UTC

from orub.db.models import (
    CollectionItemRow,
    CollectionItemTagRow,
    ReleaseRow,
    TagCategoryRow,
    TagRow,
    TrackArtistRow,
    TrackRow,
)
from orub.domain.catalog import Release, Track
from orub.domain.identity import (
    ArtistId,
    LabelId,
    ReleaseId,
    TagCategoryId,
    TagId,
    TrackId,
    TrackPosition,
)
from orub.domain.sums import Bpm, Condition, MusicalKey, RecordFormat
from orub.domain.user import CollectionItem, Tag, TagCategory, UserId


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


def tag_category_to_row(category: TagCategory) -> TagCategoryRow:
    return TagCategoryRow(id=category.id.value, user_id=category.user_id.value, name=category.name)


def tag_category_from_row(row: TagCategoryRow) -> TagCategory:
    return TagCategory(id=TagCategoryId(row.id), user_id=UserId(row.user_id), name=row.name)


def tag_to_row(tag: Tag) -> TagRow:
    return TagRow(
        id=tag.id.value,
        user_id=tag.user_id.value,
        category_id=tag.category_id.value,
        name=tag.name,
    )


def tag_from_row(row: TagRow) -> Tag:
    return Tag(
        id=TagId(row.id),
        user_id=UserId(row.user_id),
        category_id=TagCategoryId(row.category_id),
        name=row.name,
    )


def collection_item_to_row(item: CollectionItem) -> CollectionItemRow:
    return CollectionItemRow(
        user_id=item.user_id.value,
        release_id=item.release_id.value,
        condition=item.condition.value,
        notes=item.notes,
        date_added=item.date_added.astimezone(UTC).replace(tzinfo=None),
        tags=[CollectionItemTagRow(tag_id=tag_id.value) for tag_id in item.tag_ids],
    )


def collection_item_from_row(row: CollectionItemRow) -> CollectionItem:
    return CollectionItem(
        user_id=UserId(row.user_id),
        release_id=ReleaseId(row.release_id),
        condition=Condition(row.condition),
        notes=row.notes,
        date_added=row.date_added.replace(tzinfo=UTC),
        tag_ids=frozenset(TagId(t.tag_id) for t in row.tags),
    )
