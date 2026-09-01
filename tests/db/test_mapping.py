from datetime import UTC, datetime

from orub.db.mapping import (
    collection_item_from_row,
    collection_item_to_row,
    release_from_row,
    release_to_row,
    tag_category_from_row,
    tag_category_to_row,
    tag_from_row,
    tag_to_row,
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

_RELEASE = Release(
    id=ReleaseId(249504),
    title="Never Gonna Give You Up",
    label_id=LabelId(895),
    year=1987,
    format=RecordFormat.VINYL,
    catno="PB 41447",
    tracklist=(
        Track(
            id=TrackId(release_id=ReleaseId(249504), position=TrackPosition("A1")),
            title="Never Gonna Give You Up",
            artist_ids=(ArtistId(72872),),
            bpm=Bpm(113.0),
            key=MusicalKey.CAMELOT_8A,
        ),
        Track(
            id=TrackId(release_id=ReleaseId(249504), position=TrackPosition("A2")),
            title="Instrumental",
            artist_ids=(ArtistId(72872), ArtistId(1)),
        ),
    ),
)


def test_release_round_trips_through_row() -> None:
    row = release_to_row(_RELEASE)
    assert release_from_row(row) == _RELEASE


def test_release_with_no_tracks_round_trips() -> None:
    release = Release(
        id=ReleaseId(1),
        title="No Tracklist",
        label_id=LabelId(1),
        year=2000,
        format=RecordFormat.CD,
        tracklist=(),
    )
    assert release_from_row(release_to_row(release)) == release


def test_tag_category_round_trips_through_row() -> None:
    category = TagCategory(id=TagCategoryId(1), user_id=UserId(1), name="genre")
    assert tag_category_from_row(tag_category_to_row(category)) == category


def test_tag_round_trips_through_row() -> None:
    tag = Tag(id=TagId(1), user_id=UserId(1), category_id=TagCategoryId(1), name="Electronic")
    assert tag_from_row(tag_to_row(tag)) == tag


def test_collection_item_round_trips_through_row() -> None:
    item = CollectionItem(
        user_id=UserId(1),
        release_id=ReleaseId(249504),
        condition=Condition.VERY_GOOD_PLUS,
        notes="sealed",
        date_added=datetime(2026, 1, 1, tzinfo=UTC),
        tag_ids=frozenset({TagId(1), TagId(2)}),
    )
    assert collection_item_from_row(collection_item_to_row(item)) == item


def test_collection_item_with_no_tags_round_trips() -> None:
    item = CollectionItem(
        user_id=UserId(1),
        release_id=ReleaseId(1),
        condition=Condition.MINT,
        notes="",
        date_added=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert collection_item_from_row(collection_item_to_row(item)) == item
