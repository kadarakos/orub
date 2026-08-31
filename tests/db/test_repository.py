import attrs
import pytest
from sqlalchemy.orm import Session

from orub.db.repository import existing_release, save_release, update_release
from orub.db.session import make_engine
from orub.domain.catalog import Release, Track
from orub.domain.identity import ArtistId, LabelId, ReleaseId, TrackId, TrackPosition
from orub.domain.sums import Bpm, MusicalKey, RecordFormat

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


def test_update_release_overwrites_year(session: Session) -> None:
    save_release(session, _RELEASE)

    updated = attrs.evolve(_RELEASE, year=1988)
    update_release(session, updated)

    assert existing_release(session, _RELEASE.id) == updated


def test_update_release_sets_track_bpm_and_key(session: Session) -> None:
    release = attrs.evolve(
        _RELEASE,
        tracklist=(
            Track(
                id=TrackId(release_id=_RELEASE.id, position=TrackPosition("A1")),
                title="Never Gonna Give You Up",
                artist_ids=(ArtistId(72872),),
            ),
        ),
    )
    save_release(session, release)

    updated_track = attrs.evolve(release.tracklist[0], bpm=Bpm(113.0), key=MusicalKey.CAMELOT_8A)
    updated = attrs.evolve(release, tracklist=(updated_track,))
    update_release(session, updated)

    assert existing_release(session, release.id) == updated


def test_update_release_drops_tracks_removed_from_tracklist(session: Session) -> None:
    release = attrs.evolve(
        _RELEASE,
        tracklist=(
            Track(
                id=TrackId(release_id=_RELEASE.id, position=TrackPosition("A1")),
                title="Side A",
                artist_ids=(),
            ),
            Track(
                id=TrackId(release_id=_RELEASE.id, position=TrackPosition("A2")),
                title="Side B",
                artist_ids=(),
            ),
        ),
    )
    save_release(session, release)

    updated = attrs.evolve(release, tracklist=release.tracklist[:1])
    update_release(session, updated)

    assert existing_release(session, release.id) == updated
