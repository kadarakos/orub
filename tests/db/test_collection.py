from datetime import UTC, datetime

import attrs
import pytest
from sqlalchemy.orm import Session

from orub.db.collection import existing_collection_item, save_collection_item
from orub.db.repository import save_release
from orub.db.session import make_engine
from orub.domain.catalog import Release
from orub.domain.identity import LabelId, ReleaseId, TagId
from orub.domain.sums import Condition, RecordFormat
from orub.domain.user import CollectionItem, UserId

_RELEASE = Release(
    id=ReleaseId(249504),
    title="Never Gonna Give You Up",
    label_id=LabelId(895),
    year=1987,
    format=RecordFormat.VINYL,
    tracklist=(),
)

_ITEM = CollectionItem(
    user_id=UserId(1),
    release_id=_RELEASE.id,
    condition=Condition.VERY_GOOD_PLUS,
    notes="sealed",
    date_added=datetime(2026, 1, 1, tzinfo=UTC),
    tag_ids=frozenset({TagId(1), TagId(2)}),
)


@pytest.fixture
def session() -> Session:  # pyright: ignore[reportUnusedFunction]
    session = Session(make_engine("sqlite:///:memory:"))
    save_release(session, _RELEASE)
    return session


def test_existing_collection_item_is_none_before_saving(session: Session) -> None:
    assert existing_collection_item(session, _ITEM.user_id, _ITEM.release_id) is None


def test_existing_collection_item_returns_saved_item(session: Session) -> None:
    save_collection_item(session, _ITEM)

    assert existing_collection_item(session, _ITEM.user_id, _ITEM.release_id) == _ITEM


def test_save_collection_item_updates_existing_instead_of_duplicating(session: Session) -> None:
    save_collection_item(session, _ITEM)

    updated = attrs.evolve(_ITEM, notes="resealed", tag_ids=frozenset({TagId(3)}))
    save_collection_item(session, updated)

    assert existing_collection_item(session, _ITEM.user_id, _ITEM.release_id) == updated
