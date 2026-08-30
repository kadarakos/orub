import pytest
from sqlalchemy.orm import Session

from orub.db.repository import existing_release, save_release
from orub.db.session import make_engine
from orub.domain.catalog import Release
from orub.domain.identity import LabelId, ReleaseId
from orub.domain.sums import RecordFormat

_RELEASE = Release(
    id=ReleaseId(249504),
    title="Never Gonna Give You Up",
    label_id=LabelId(895),
    year=1987,
    format=RecordFormat.VINYL,
    tracklist=(),
)


@pytest.fixture
def session() -> Session:  # pyright: ignore[reportUnusedFunction]
    return Session(make_engine("sqlite:///:memory:"))


def test_existing_release_is_none_before_saving(session: Session) -> None:
    assert existing_release(session, ReleaseId(249504)) is None


def test_existing_release_returns_saved_release(session: Session) -> None:
    save_release(session, _RELEASE)

    assert existing_release(session, _RELEASE.id) == _RELEASE


def test_existing_release_does_not_match_a_different_id(session: Session) -> None:
    save_release(session, _RELEASE)

    assert existing_release(session, ReleaseId(1)) is None
