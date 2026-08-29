from orub.domain.identity import ArtistId, ReleaseId, TrackId, TrackPosition


def test_ids_are_frozen_and_compare_by_value() -> None:
    assert ArtistId(1) == ArtistId(1)
    assert ArtistId(1) != ArtistId(2)
    assert ArtistId(1) != ReleaseId(1)


def test_ids_are_hashable() -> None:
    assert len({ArtistId(1), ArtistId(1), ArtistId(2)}) == 2


def test_track_id_is_composite_of_release_and_position() -> None:
    release_id = ReleaseId(42)
    track_id = TrackId(release_id=release_id, position=TrackPosition("A1"))

    assert track_id.release_id == release_id
    assert track_id.position == TrackPosition("A1")


def test_track_ids_differ_by_position_within_same_release() -> None:
    release_id = ReleaseId(42)
    a1 = TrackId(release_id=release_id, position=TrackPosition("A1"))
    b1 = TrackId(release_id=release_id, position=TrackPosition("B1"))

    assert a1 != b1
