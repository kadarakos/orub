"""Orchestrates release ingestion, either by id or by search.

See design doc §4.2, §3 (IngestOutcome). Both entry points are pure: fetch,
search, and the existing-release lookup are all injected as callables, so
they're testable with fakes and don't know about HTTP or a database. The
real `DiscogsClient` methods (impure edge) and a real DB-backed lookup
(Phase 3, not built yet) are wired in by the caller -- see cli.py for the
current "always None" lookup stand-in.

`ingest_release_by_search` always ingests the *full* release once a match
is unambiguous: it never maps a thin `DiscogsSearchResultDTO` into a
`Release` itself, it hands the resolved id to `ingest_release_by_id`, which
does the real fetch + mapping. Search only narrows down *which* release.
"""

from __future__ import annotations

from collections.abc import Callable

import attrs

from orub.discogs.errors import FetchError, MalformedResponse
from orub.discogs.mapping import DiscogsTagHints, release_from_dto, tag_hints_from_dto
from orub.discogs.models import DiscogsReleaseDTO, DiscogsSearchResultDTO
from orub.domain.catalog import Release
from orub.domain.identity import ReleaseId
from orub.domain.ingest_outcome import (
    AlreadyExists,
    AmbiguousMatch,
    Created,
    IngestOutcome,
    NotFound,
)
from orub.domain.result import Err, Ok, Result


@attrs.frozen(slots=True)
class ReleaseSearchQuery:
    release_title: str | None = None
    track_title: str | None = None
    artist: str | None = None
    label: str | None = None
    year: int | None = None
    catno: str | None = None


@attrs.frozen(slots=True)
class IngestResult[T, C]:
    """An `IngestOutcome` plus whatever Discogs tag vocabulary (genre/style/
    format) came with it. `tag_hints` is empty whenever no release DTO was
    actually fetched (NotFound, AmbiguousMatch) -- there's nothing to derive
    tags from yet.
    """

    outcome: IngestOutcome[T, C]
    tag_hints: DiscogsTagHints = attrs.field(factory=DiscogsTagHints)


type FetchRelease = Callable[[ReleaseId], Result[DiscogsReleaseDTO | None, FetchError]]
type ExistingRelease = Callable[[ReleaseId], Release | None]
type SearchReleases = Callable[
    [ReleaseSearchQuery], Result[tuple[DiscogsSearchResultDTO, ...], FetchError]
]


def ingest_release_by_id(
    fetch_release: FetchRelease,
    existing_release: ExistingRelease,
    release_id: ReleaseId,
) -> Result[IngestResult[Release, DiscogsSearchResultDTO], FetchError]:
    fetched = fetch_release(release_id)
    match fetched:
        case Err() as err:
            return err
        case Ok(value=dto):
            if dto is None:
                return Ok(IngestResult(NotFound()))
            match release_from_dto(dto):
                case Err(error=reason):
                    return Err(MalformedResponse(reason))
                case Ok(value=release):
                    hints = tag_hints_from_dto(dto)
                    if existing_release(release.id) is not None:
                        return Ok(IngestResult(AlreadyExists(release), hints))
                    return Ok(IngestResult(Created(release), hints))


def ingest_release_by_search(
    search: SearchReleases,
    fetch_release: FetchRelease,
    existing_release: ExistingRelease,
    query: ReleaseSearchQuery,
) -> Result[IngestResult[Release, DiscogsSearchResultDTO], FetchError]:
    match search(query):
        case Err() as err:
            return err
        case Ok(value=results):
            if len(results) == 0:
                return Ok(IngestResult(NotFound()))
            if len(results) > 1:
                return Ok(IngestResult(AmbiguousMatch(results)))
            return ingest_release_by_id(
                fetch_release=fetch_release,
                existing_release=existing_release,
                release_id=ReleaseId(results[0].id),
            )
