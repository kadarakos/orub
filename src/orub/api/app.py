"""FastAPI layer. See design doc §4.5, §8.

Deliberately scoped to the search -> ingest flow for this slice, so the Elm
frontend has something to talk to instead of calling Python directly. No
auth yet -- single implicit user, same as the CLI; real auth waits for the
user-owned-table slice of Phase 3, per TODO.md. Wires the same pure
`ingest_release_by_search`/`ingest_release_by_id` pipelines the CLI uses,
with `DiscogsClient` and a DB `Session` as the impure edge here instead of
typer. `POST /releases/{id}/ingest` reuses `SearchResponse` as its response
model (rather than a narrower type) even though it can never actually
return "ambiguous" -- same tolerance the CLI's `ingest-release` command
already applies to its unreachable `AmbiguousMatch` match arm.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from orub.config import Settings
from orub.db.repository import existing_release as lookup_existing_release
from orub.db.repository import save_release
from orub.db.session import make_engine
from orub.discogs.client import DiscogsClient
from orub.discogs.errors import FetchError, MalformedResponse, NetworkError, RateLimited
from orub.discogs.ingest import ReleaseSearchQuery, ingest_release_by_id, ingest_release_by_search
from orub.discogs.models import DiscogsSearchResultDTO
from orub.domain.catalog import Release
from orub.domain.identity import ReleaseId
from orub.domain.ingest_outcome import AlreadyExists, AmbiguousMatch, Created, NotFound
from orub.domain.result import Err, Ok, Result

logger = logging.getLogger(__name__)

# Dev-level logging: prints FetchError detail (e.g. an unsupported
# RecordFormat/label discovered live) to stderr, since uvicorn's default
# config doesn't attach a handler to the root logger. Revisit with
# structured/leveled config before deployment (design doc §7).
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = Settings()  # type: ignore[call-arg]
    app.state.settings = settings
    app.state.engine = make_engine(settings.database_url)
    yield


app = FastAPI(title="orub", lifespan=_lifespan)

# Single personal-use frontend, run locally during development -- no
# credentials/cookies involved (no auth yet), so a permissive dev CORS
# policy is fine; revisit once this is actually deployed (design doc §7).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    release_title: str | None = None
    track_title: str | None = None
    artist: str | None = None
    label: str | None = None
    year: int | None = None


class ReleaseResponse(BaseModel):
    id: int
    title: str
    year: int
    format: str


class CandidateResponse(BaseModel):
    id: int
    title: str
    year: int | None
    label: list[str]
    format: list[str]


class SearchResponse(BaseModel):
    status: Literal["created", "already_exists", "ambiguous", "not_found"]
    release: ReleaseResponse | None = None
    candidates: list[CandidateResponse] | None = None


def _release_response(release: Release) -> ReleaseResponse:
    return ReleaseResponse(
        id=release.id.value, title=release.title, year=release.year, format=release.format.value
    )


def _candidate_response(candidate: DiscogsSearchResultDTO) -> CandidateResponse:
    return CandidateResponse(
        id=candidate.id,
        title=candidate.title,
        year=candidate.year,
        label=candidate.label,
        format=candidate.format,
    )


def _fetch_error_to_http(error: FetchError) -> HTTPException:
    match error:
        case NetworkError(message=message):
            return HTTPException(status_code=502, detail=f"Network error: {message}")
        case RateLimited(retry_after_seconds=retry_after):
            return HTTPException(
                status_code=429, detail=f"Rate limited (retry after {retry_after}s)"
            )
        case MalformedResponse(message=message):
            return HTTPException(status_code=502, detail=f"Malformed response: {message}")


@app.post("/releases/search", response_model=SearchResponse)
def search_release(body: SearchRequest, http_request: Request) -> SearchResponse:
    settings: Settings = http_request.app.state.settings
    engine = http_request.app.state.engine
    query = ReleaseSearchQuery(
        release_title=body.release_title,
        track_title=body.track_title,
        artist=body.artist,
        label=body.label,
        year=body.year,
    )

    with (
        DiscogsClient(
            token=settings.discogs_token, user_agent=settings.discogs_user_agent
        ) as client,
        Session(engine) as session,
    ):

        def _search(
            query: ReleaseSearchQuery,
        ) -> Result[tuple[DiscogsSearchResultDTO, ...], FetchError]:
            return client.search_releases(
                release_title=query.release_title,
                track_title=query.track_title,
                artist=query.artist,
                label=query.label,
                year=query.year,
            )

        result = ingest_release_by_search(
            search=_search,
            fetch_release=client.fetch_release,
            existing_release=lambda rid: lookup_existing_release(session, rid),
            query=query,
        )

        match result:
            case Err(error=error):
                logger.warning("search failed for query=%r: %s", query, error)
                raise _fetch_error_to_http(error)
            case Ok(value=outcome):
                match outcome:
                    case Created(value=release):
                        save_release(session, release)
                        return SearchResponse(status="created", release=_release_response(release))
                    case AlreadyExists(value=release):
                        return SearchResponse(
                            status="already_exists", release=_release_response(release)
                        )
                    case AmbiguousMatch(candidates=candidates):
                        return SearchResponse(
                            status="ambiguous",
                            candidates=[_candidate_response(c) for c in candidates],
                        )
                    case NotFound():
                        return SearchResponse(status="not_found")


@app.post("/releases/{release_id}/ingest", response_model=SearchResponse)
def ingest_release(release_id: int, http_request: Request) -> SearchResponse:
    settings: Settings = http_request.app.state.settings
    engine = http_request.app.state.engine

    with (
        DiscogsClient(
            token=settings.discogs_token, user_agent=settings.discogs_user_agent
        ) as client,
        Session(engine) as session,
    ):
        result = ingest_release_by_id(
            fetch_release=client.fetch_release,
            existing_release=lambda rid: lookup_existing_release(session, rid),
            release_id=ReleaseId(release_id),
        )

        match result:
            case Err(error=error):
                logger.warning("ingest failed for release_id=%s: %s", release_id, error)
                raise _fetch_error_to_http(error)
            case Ok(value=outcome):
                match outcome:
                    case Created(value=release):
                        save_release(session, release)
                        return SearchResponse(status="created", release=_release_response(release))
                    case AlreadyExists(value=release):
                        return SearchResponse(
                            status="already_exists", release=_release_response(release)
                        )
                    case AmbiguousMatch(candidates=candidates):
                        return SearchResponse(
                            status="ambiguous",
                            candidates=[_candidate_response(c) for c in candidates],
                        )
                    case NotFound():
                        return SearchResponse(status="not_found")
