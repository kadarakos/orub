from orub.db.mapping import release_from_row, release_to_row
from orub.domain.catalog import Release, Track
from orub.domain.identity import ArtistId, LabelId, ReleaseId, TrackId, TrackPosition
from orub.domain.sums import Bpm, MusicalKey, RecordFormat

_RELEASE = Release(
    id=ReleaseId(249504),
    title="Never Gonna Give You Up",
    label_id=LabelId(895),
    year=1987,
    format=RecordFormat.VINYL,
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
