from orub.discogs.errors import NetworkError
from orub.discogs.ingest import (
    IngestResult,
    ReleaseSearchQuery,
    ingest_release_by_id,
    ingest_release_by_search,
)
from orub.discogs.mapping import DiscogsTagHints
from orub.discogs.models import (
    DiscogsArtistDTO,
    DiscogsFormatDTO,
    DiscogsLabelDTO,
    DiscogsReleaseDTO,
    DiscogsSearchResultDTO,
)
from orub.domain.catalog import Release
from orub.domain.identity import LabelId, ReleaseId
from orub.domain.ingest_outcome import AlreadyExists, AmbiguousMatch, Created, NotFound
from orub.domain.result import Err, Ok
from orub.domain.sums import RecordFormat

_DTO = DiscogsReleaseDTO(
    id=249504,
    title="Never Gonna Give You Up",
    artists=[DiscogsArtistDTO(id=72872, name="Rick Astley")],
    labels=[DiscogsLabelDTO(id=895, name="RCA")],
    year=1987,
    formats=[DiscogsFormatDTO(name="Vinyl")],
    tracklist=[],
)

_EXPECTED_RELEASE = Release(
    id=ReleaseId(249504),
    title="Never Gonna Give You Up",
    label_id=LabelId(895),
    year=1987,
    format=RecordFormat.VINYL,
    tracklist=(),
)


def _no_existing_release(release_id: ReleaseId) -> Release | None:
    return None


def _created(
    release: Release, hints: DiscogsTagHints | None = None
) -> IngestResult[Release, DiscogsSearchResultDTO]:
    return IngestResult(Created(release), hints if hints is not None else DiscogsTagHints())


def _already_exists(release: Release) -> IngestResult[Release, DiscogsSearchResultDTO]:
    return IngestResult(AlreadyExists(release))


def _not_found() -> IngestResult[Release, DiscogsSearchResultDTO]:
    return IngestResult(NotFound())


def _ambiguous(
    *candidates: DiscogsSearchResultDTO,
) -> IngestResult[Release, DiscogsSearchResultDTO]:
    return IngestResult(AmbiguousMatch(candidates))


def test_ingest_creates_new_release() -> None:
    result = ingest_release_by_id(
        fetch_release=lambda _: Ok(_DTO),
        existing_release=_no_existing_release,
        release_id=ReleaseId(249504),
    )

    assert result == Ok(_created(_EXPECTED_RELEASE))


def test_ingest_reports_already_exists() -> None:
    result = ingest_release_by_id(
        fetch_release=lambda _: Ok(_DTO),
        existing_release=lambda release_id: _EXPECTED_RELEASE,
        release_id=ReleaseId(249504),
    )

    assert result == Ok(_already_exists(_EXPECTED_RELEASE))


def test_ingest_reports_not_found() -> None:
    result = ingest_release_by_id(
        fetch_release=lambda _: Ok(None),
        existing_release=_no_existing_release,
        release_id=ReleaseId(1),
    )

    assert result == Ok(_not_found())


def test_ingest_extracts_tag_hints_from_dto() -> None:
    dto_with_tags = DiscogsReleaseDTO(
        id=249504,
        title="Never Gonna Give You Up",
        artists=[DiscogsArtistDTO(id=72872, name="Rick Astley")],
        labels=[DiscogsLabelDTO(id=895, name="RCA")],
        year=1987,
        formats=[DiscogsFormatDTO(name="Vinyl", descriptions=["Single"])],
        tracklist=[],
        genres=["Pop"],
        styles=["Synth-pop"],
    )
    result = ingest_release_by_id(
        fetch_release=lambda _: Ok(dto_with_tags),
        existing_release=_no_existing_release,
        release_id=ReleaseId(249504),
    )

    assert result == Ok(
        _created(
            Release(
                id=ReleaseId(249504),
                title="Never Gonna Give You Up",
                label_id=LabelId(895),
                year=1987,
                format=RecordFormat.VINYL,
                tracklist=(),
            ),
            DiscogsTagHints(
                genres=("Pop",), styles=("Synth-pop",), format_descriptions=("Single",)
            ),
        )
    )


def test_ingest_propagates_fetch_error() -> None:
    error = NetworkError("boom")
    result = ingest_release_by_id(
        fetch_release=lambda _: Err(error),
        existing_release=_no_existing_release,
        release_id=ReleaseId(1),
    )

    assert result == Err(error)


def test_ingest_surfaces_mapping_failure_as_malformed_response() -> None:
    unsupported_format_dto = DiscogsReleaseDTO(
        id=1,
        title="Weird Format",
        artists=[DiscogsArtistDTO(id=1, name="Someone")],
        labels=[DiscogsLabelDTO(id=1, name="Some Label")],
        formats=[DiscogsFormatDTO(name="Betamax")],
        tracklist=[],
    )
    result = ingest_release_by_id(
        fetch_release=lambda _: Ok(unsupported_format_dto),
        existing_release=_no_existing_release,
        release_id=ReleaseId(1),
    )

    assert isinstance(result, Err)


_SEARCH_RESULT = DiscogsSearchResultDTO(id=249504, title="Rick Astley - Never Gonna Give You Up")
_OTHER_SEARCH_RESULT = DiscogsSearchResultDTO(id=1, title="Rick Astley - Some Other Pressing")
_QUERY = ReleaseSearchQuery(release_title="Never Gonna Give You Up", artist="Rick Astley")


def test_search_ingest_creates_release_on_unique_match() -> None:
    result = ingest_release_by_search(
        search=lambda _: Ok((_SEARCH_RESULT,)),
        fetch_release=lambda _: Ok(_DTO),
        existing_release=_no_existing_release,
        query=_QUERY,
    )

    assert result == Ok(_created(_EXPECTED_RELEASE))


def test_search_ingest_reports_already_exists_on_unique_match() -> None:
    result = ingest_release_by_search(
        search=lambda _: Ok((_SEARCH_RESULT,)),
        fetch_release=lambda _: Ok(_DTO),
        existing_release=lambda release_id: _EXPECTED_RELEASE,
        query=_QUERY,
    )

    assert result == Ok(_already_exists(_EXPECTED_RELEASE))


def test_search_ingest_reports_ambiguous_match_on_multiple_results() -> None:
    result = ingest_release_by_search(
        search=lambda _: Ok((_SEARCH_RESULT, _OTHER_SEARCH_RESULT)),
        fetch_release=lambda _: Ok(_DTO),
        existing_release=_no_existing_release,
        query=_QUERY,
    )

    assert result == Ok(_ambiguous(_SEARCH_RESULT, _OTHER_SEARCH_RESULT))


def test_search_ingest_reports_not_found_on_no_results() -> None:
    result = ingest_release_by_search(
        search=lambda _: Ok(()),
        fetch_release=lambda _: Ok(_DTO),
        existing_release=_no_existing_release,
        query=_QUERY,
    )

    assert result == Ok(_not_found())


def test_search_ingest_propagates_search_error() -> None:
    error = NetworkError("boom")
    result = ingest_release_by_search(
        search=lambda _: Err(error),
        fetch_release=lambda _: Ok(_DTO),
        existing_release=_no_existing_release,
        query=_QUERY,
    )

    assert result == Err(error)


def test_search_ingest_propagates_fetch_error_on_unique_match() -> None:
    error = NetworkError("boom")
    result = ingest_release_by_search(
        search=lambda _: Ok((_SEARCH_RESULT,)),
        fetch_release=lambda _: Err(error),
        existing_release=_no_existing_release,
        query=_QUERY,
    )

    assert result == Err(error)
