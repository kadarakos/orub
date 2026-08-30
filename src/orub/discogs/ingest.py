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
from orub.discogs.mapping import release_from_dto
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


type FetchRelease = Callable[[ReleaseId], Result[DiscogsReleaseDTO | None, FetchError]]
type ExistingRelease = Callable[[ReleaseId], Release | None]
type SearchReleases = Callable[
    [ReleaseSearchQuery], Result[tuple[DiscogsSearchResultDTO, ...], FetchError]
]


def ingest_release_by_id(
    fetch_release: FetchRelease,
    existing_release: ExistingRelease,
    release_id: ReleaseId,
) -> Result[IngestOutcome[Release, DiscogsSearchResultDTO], FetchError]:
    fetched = fetch_release(release_id)
    match fetched:
        case Err() as err:
            return err
        case Ok(value=dto):
            if dto is None:
                return Ok(NotFound())
            match release_from_dto(dto):
                case Err(error=reason):
                    return Err(MalformedResponse(reason))
                case Ok(value=release):
                    if existing_release(release.id) is not None:
                        return Ok(AlreadyExists(release))
                    return Ok(Created(release))


def ingest_release_by_search(
    search: SearchReleases,
    fetch_release: FetchRelease,
    existing_release: ExistingRelease,
    query: ReleaseSearchQuery,
) -> Result[IngestOutcome[Release, DiscogsSearchResultDTO], FetchError]:
    match search(query):
        case Err() as err:
            return err
        case Ok(value=results):
            if len(results) == 0:
                return Ok(NotFound())
            if len(results) > 1:
                return Ok(AmbiguousMatch(results))
            return ingest_release_by_id(
                fetch_release=fetch_release,
                existing_release=existing_release,
                release_id=ReleaseId(results[0].id),
            )
