import pytest
from sqlalchemy.orm import Session

from orub.db.session import make_engine
from orub.db.tags import (
    apply_discogs_tag_hints,
    get_or_create_tag,
    get_or_create_tag_category,
    list_tag_categories,
    list_tags,
)
from orub.discogs.mapping import DiscogsTagHints
from orub.domain.identity import UserId


@pytest.fixture
def session() -> Session:  # pyright: ignore[reportUnusedFunction]
    return Session(make_engine("sqlite:///:memory:"))


_USER = UserId(1)


def test_get_or_create_tag_category_creates_once(session: Session) -> None:
    first = get_or_create_tag_category(session, _USER, "genre")
    second = get_or_create_tag_category(session, _USER, "genre")

    assert first.id == second.id
    assert first.name == "genre"


def test_get_or_create_tag_creates_once(session: Session) -> None:
    category = get_or_create_tag_category(session, _USER, "genre")

    first = get_or_create_tag(session, _USER, category.id, "Electronic")
    second = get_or_create_tag(session, _USER, category.id, "Electronic")

    assert first.id == second.id
    assert first.name == "Electronic"
    assert first.category_id == category.id


def test_apply_discogs_tag_hints_creates_categories_and_tags(session: Session) -> None:
    hints = DiscogsTagHints(
        genres=("Electronic",), styles=("IDM", "Acid"), format_descriptions=("Album",)
    )

    tag_ids = apply_discogs_tag_hints(session, _USER, hints)

    assert len(tag_ids) == 4
    assert len(set(tag_ids)) == 4


def test_apply_discogs_tag_hints_is_idempotent(session: Session) -> None:
    hints = DiscogsTagHints(genres=("Electronic",), styles=("IDM",))

    first = apply_discogs_tag_hints(session, _USER, hints)
    second = apply_discogs_tag_hints(session, _USER, hints)

    assert first == second


def test_apply_discogs_tag_hints_with_no_hints_creates_nothing(session: Session) -> None:
    tag_ids = apply_discogs_tag_hints(session, _USER, DiscogsTagHints())

    assert tag_ids == ()


def test_list_tag_categories_returns_categories_sorted_by_name(session: Session) -> None:
    get_or_create_tag_category(session, _USER, "style")
    get_or_create_tag_category(session, _USER, "genre")

    categories = list_tag_categories(session, _USER)

    assert [c.name for c in categories] == ["genre", "style"]


def test_list_tags_returns_only_tags_in_that_category(session: Session) -> None:
    genre = get_or_create_tag_category(session, _USER, "genre")
    style = get_or_create_tag_category(session, _USER, "style")
    get_or_create_tag(session, _USER, genre.id, "Electronic")
    get_or_create_tag(session, _USER, style.id, "IDM")

    tags = list_tags(session, _USER, genre.id)

    assert [t.name for t in tags] == ["Electronic"]
