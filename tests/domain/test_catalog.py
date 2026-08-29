from orub.domain.catalog import Artist, Label, Release, Track
from orub.domain.identity import ArtistId, LabelId, ReleaseId, TrackId, TrackPosition
from orub.domain.sums import Bpm, MusicalKey, RecordFormat


def _track(position: str) -> Track:
    return Track(
        id=TrackId(release_id=ReleaseId(1), position=TrackPosition(position)),
        title=f"Track {position}",
        artist_ids=(ArtistId(1),),
    )


def test_track_bpm_and_key_default_to_none() -> None:
    track = _track("A1")
    assert track.bpm is None
    assert track.key is None


def test_track_bpm_and_key_can_be_set() -> None:
    track = Track(
        id=TrackId(release_id=ReleaseId(1), position=TrackPosition("A1")),
        title="Intro",
        artist_ids=(ArtistId(1),),
        bpm=Bpm(120.0),
        key=MusicalKey.CAMELOT_8A,
    )
    assert track.bpm == Bpm(120.0)
    assert track.key == MusicalKey.CAMELOT_8A


def test_release_holds_tracklist_and_label_reference() -> None:
    tracklist = (_track("A1"), _track("A2"))
    release = Release(
        id=ReleaseId(1),
        title="Some Release",
        label_id=LabelId(1),
        year=1998,
        format=RecordFormat.VINYL,
        tracklist=tracklist,
    )

    assert release.tracklist == tracklist
    assert release.label_id == LabelId(1)


def test_catalog_entities_are_frozen_and_compare_by_value() -> None:
    assert Artist(ArtistId(1), "Some Artist") == Artist(ArtistId(1), "Some Artist")
    assert Label(LabelId(1), "Some Label") == Label(LabelId(1), "Some Label")
