from datetime import UTC, datetime

from orub.domain.identity import ReleaseId, TagCategoryId, TagId, TrackId, TrackPosition, UserId
from orub.domain.sums import Condition, EdgeSource
from orub.domain.user import CollectionItem, Edge, Tag, TagCategory


def test_collection_item_defaults_to_no_tags() -> None:
    item = CollectionItem(
        user_id=UserId(1),
        release_id=ReleaseId(1),
        condition=Condition.VERY_GOOD_PLUS,
        notes="",
        date_added=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert item.tag_ids == frozenset()


def test_collection_item_can_carry_tags_across_categories() -> None:
    item = CollectionItem(
        user_id=UserId(1),
        release_id=ReleaseId(1),
        condition=Condition.MINT,
        notes="sealed",
        date_added=datetime(2026, 1, 1, tzinfo=UTC),
        tag_ids=frozenset({TagId(1), TagId(2)}),
    )
    assert item.tag_ids == frozenset({TagId(1), TagId(2)})


def test_tag_belongs_to_a_category_and_a_user() -> None:
    tag = Tag(id=TagId(1), user_id=UserId(1), category_id=TagCategoryId(1), name="Chill")
    category = TagCategory(id=TagCategoryId(1), user_id=UserId(1), name="Mood")
    assert tag.category_id == category.id
    assert tag.user_id == category.user_id


def test_edge_connects_two_tracks_for_one_user() -> None:
    release_id = ReleaseId(1)
    edge = Edge(
        from_track_id=TrackId(release_id, TrackPosition("A1")),
        to_track_id=TrackId(release_id, TrackPosition("A2")),
        source=EdgeSource.MANUAL,
        user_id=UserId(1),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert edge.weight is None
    assert edge.source is EdgeSource.MANUAL


def test_edge_can_carry_a_compatibility_weight() -> None:
    release_id = ReleaseId(1)
    edge = Edge(
        from_track_id=TrackId(release_id, TrackPosition("A1")),
        to_track_id=TrackId(release_id, TrackPosition("A2")),
        source=EdgeSource.AUTO,
        user_id=UserId(1),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        weight=0.8,
    )
    assert edge.weight == 0.8
