from orub.discogs.mapping import release_from_dto
from orub.discogs.models import (
    DiscogsArtistDTO,
    DiscogsFormatDTO,
    DiscogsLabelDTO,
    DiscogsReleaseDTO,
    DiscogsTrackDTO,
)
from orub.domain.identity import ArtistId, LabelId, ReleaseId, TrackId, TrackPosition
from orub.domain.result import Err, Ok
from orub.domain.sums import RecordFormat


def _release_dto(**overrides: object) -> DiscogsReleaseDTO:
    defaults: dict[str, object] = {
        "id": 249504,
        "title": "Never Gonna Give You Up",
        "artists": [DiscogsArtistDTO(id=72872, name="Rick Astley")],
        "labels": [DiscogsLabelDTO(id=895, name="RCA")],
        "year": 1987,
        "formats": [DiscogsFormatDTO(name="Vinyl")],
        "tracklist": [
            DiscogsTrackDTO(position="A", title="Never Gonna Give You Up"),
            DiscogsTrackDTO(position="B", title="Never Gonna Give You Up (Instrumental)"),
        ],
    }
    defaults.update(overrides)
    return DiscogsReleaseDTO.model_validate(defaults)


def test_maps_release_fields() -> None:
    result = release_from_dto(_release_dto())

    assert isinstance(result, Ok)
    release = result.value
    assert release.id == ReleaseId(249504)
    assert release.title == "Never Gonna Give You Up"
    assert release.label_id == LabelId(895)
    assert release.year == 1987
    assert release.format == RecordFormat.VINYL


def test_maps_tracklist_inheriting_release_artists() -> None:
    result = release_from_dto(_release_dto())

    assert isinstance(result, Ok)
    tracks = result.value.tracklist
    assert len(tracks) == 2
    assert tracks[0].id == TrackId(ReleaseId(249504), TrackPosition("A"))
    assert tracks[0].artist_ids == (ArtistId(72872),)


def test_track_level_artists_override_release_artists() -> None:
    dto = _release_dto(
        tracklist=[
            DiscogsTrackDTO(
                position="A",
                title="Feat. Someone Else",
                artists=[DiscogsArtistDTO(id=1, name="Someone Else")],
            )
        ]
    )
    result = release_from_dto(dto)

    assert isinstance(result, Ok)
    assert result.value.tracklist[0].artist_ids == (ArtistId(1),)


def test_dedupes_duplicate_track_level_artist_credits() -> None:
    # Discogs credits the same artist twice on some releases (e.g. a
    # Latin-script name and a transliteration joined by "=" on
    # Japanese-market releases) -- both entries share the same id.
    dto = _release_dto(
        tracklist=[
            DiscogsTrackDTO(
                position="A",
                title="Feed Me Weird Things",
                artists=[
                    DiscogsArtistDTO(id=269, name="Squarepusher"),
                    DiscogsArtistDTO(id=269, name="スクエアプッシャー"),
                ],
            )
        ]
    )
    result = release_from_dto(dto)

    assert isinstance(result, Ok)
    assert result.value.tracklist[0].artist_ids == (ArtistId(269),)


def test_dedupes_duplicate_release_level_artist_credits() -> None:
    dto = _release_dto(
        artists=[
            DiscogsArtistDTO(id=269, name="Squarepusher"),
            DiscogsArtistDTO(id=269, name="スクエアプッシャー"),
        ]
    )
    result = release_from_dto(dto)

    assert isinstance(result, Ok)
    assert result.value.tracklist[0].artist_ids == (ArtistId(269),)


def test_skips_heading_entries_without_position() -> None:
    dto = _release_dto(
        tracklist=[
            DiscogsTrackDTO(position="", title="Side A", type="heading"),
            DiscogsTrackDTO(position="A1", title="Real Track"),
        ]
    )
    result = release_from_dto(dto)

    assert isinstance(result, Ok)
    assert len(result.value.tracklist) == 1
    assert result.value.tracklist[0].title == "Real Track"


def test_maps_file_format() -> None:
    dto = _release_dto(formats=[DiscogsFormatDTO(name="File")])
    result = release_from_dto(dto)

    assert isinstance(result, Ok)
    assert result.value.format == RecordFormat.FILE


def test_maps_lathe_cut_format() -> None:
    dto = _release_dto(formats=[DiscogsFormatDTO(name="Lathe Cut")])
    result = release_from_dto(dto)

    assert isinstance(result, Ok)
    assert result.value.format == RecordFormat.LATHE_CUT


def test_unsupported_format_is_a_mapping_error() -> None:
    dto = _release_dto(formats=[DiscogsFormatDTO(name="Betamax")])
    result = release_from_dto(dto)

    assert isinstance(result, Err)


def test_empty_formats_is_a_mapping_error() -> None:
    dto = _release_dto(formats=[])
    result = release_from_dto(dto)

    assert isinstance(result, Err)


def test_missing_label_is_a_mapping_error() -> None:
    dto = _release_dto(labels=[])
    result = release_from_dto(dto)

    assert isinstance(result, Err)
