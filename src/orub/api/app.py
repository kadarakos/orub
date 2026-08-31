"""FastAPI layer. See design doc §4.5, §8.

Covers the search -> ingest flow plus the "Add details" step that follows
it: editing a release's year/track bpm/key, browsing/creating tags, and
attaching a release to the user's collection. No auth yet -- single
implicit user, same as the CLI; real auth waits for a later Phase 3 slice,
per TODO.md. Wires the same pure `ingest_release_by_search`/
`ingest_release_by_id` pipelines the CLI uses, with `DiscogsClient` and a
DB `Session` as the impure edge here instead of typer. `POST
/releases/{id}/ingest` reuses `SearchResponse` as its response model
(rather than a narrower type) even though it can never actually return
"ambiguous" -- same tolerance the CLI's `ingest-release` command already
applies to its unreachable `AmbiguousMatch` match arm.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Literal

import attrs
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from orub.config import Settings
from orub.db.collection import save_collection_item
from orub.db.repository import existing_release as lookup_existing_release
from orub.db.repository import save_release, update_release
from orub.db.session import make_engine
from orub.db.tags import (
    apply_discogs_tag_hints,
    get_or_create_tag,
    get_or_create_tag_category,
    list_tag_categories,
    list_tags,
)
from orub.discogs.client import DiscogsClient
from orub.discogs.errors import FetchError, MalformedResponse, NetworkError, RateLimited
from orub.discogs.ingest import ReleaseSearchQuery, ingest_release_by_id, ingest_release_by_search
from orub.discogs.models import DiscogsSearchResultDTO
from orub.domain.catalog import Release, Track
from orub.domain.identity import ReleaseId, TagId
from orub.domain.ingest_outcome import AlreadyExists, AmbiguousMatch, Created, NotFound
from orub.domain.result import Err, Ok, Result
from orub.domain.sums import Bpm, Condition, MusicalKey
from orub.domain.user import DEFAULT_USER_ID, CollectionItem

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
    year: int | None
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
    suggested_tag_ids: list[int] | None = None


class TrackResponse(BaseModel):
    position: str
    title: str
    bpm: float | None
    key: str | None


class ReleaseDetailResponse(BaseModel):
    id: int
    title: str
    year: int | None
    format: str
    tracks: list[TrackResponse]


class TrackEditRequest(BaseModel):
    position: str
    bpm: float | None = None
    key: str | None = None


class ReleaseEditRequest(BaseModel):
    year: int | None
    tracks: list[TrackEditRequest] = []


class TagResponse(BaseModel):
    id: int
    name: str


class TagCategoryResponse(BaseModel):
    id: int
    name: str
    tags: list[TagResponse]


class CreateTagRequest(BaseModel):
    category: str
    name: str


class CreateCollectionItemRequest(BaseModel):
    release_id: int
    condition: Condition
    notes: str = ""
    tag_ids: list[int] = []


class CollectionItemResponse(BaseModel):
    release_id: int
    condition: str
    notes: str
    date_added: datetime
    tag_ids: list[int]


def _release_response(release: Release) -> ReleaseResponse:
    return ReleaseResponse(
        id=release.id.value, title=release.title, year=release.year, format=release.format.value
    )


def _release_detail_response(release: Release) -> ReleaseDetailResponse:
    return ReleaseDetailResponse(
        id=release.id.value,
        title=release.title,
        year=release.year,
        format=release.format.value,
        tracks=[
            TrackResponse(
                position=track.id.position.value,
                title=track.title,
                bpm=track.bpm.value if track.bpm is not None else None,
                key=track.key.value if track.key is not None else None,
            )
            for track in release.tracklist
        ],
    )


def _apply_release_edit(release: Release, body: ReleaseEditRequest) -> Result[Release, str]:
    edits_by_position = {edit.position: edit for edit in body.tracks}
    updated_tracks: list[Track] = []
    for track in release.tracklist:
        edit = edits_by_position.pop(track.id.position.value, None)
        if edit is None:
            updated_tracks.append(track)
            continue
        try:
            bpm = Bpm(edit.bpm) if edit.bpm is not None else None
            key = MusicalKey(edit.key) if edit.key is not None else None
        except ValueError as error:
            return Err(str(error))
        updated_tracks.append(attrs.evolve(track, bpm=bpm, key=key))
    if edits_by_position:
        return Err(f"unknown track position(s): {sorted(edits_by_position)}")
    return Ok(attrs.evolve(release, year=body.year, tracklist=tuple(updated_tracks)))


def _collection_item_response(item: CollectionItem) -> CollectionItemResponse:
    return CollectionItemResponse(
        release_id=item.release_id.value,
        condition=item.condition.value,
        notes=item.notes,
        date_added=item.date_added,
        tag_ids=[tag_id.value for tag_id in item.tag_ids],
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
            case Ok(value=ingest_result):
                match ingest_result.outcome:
                    case Created(value=release):
                        save_release(session, release)
                        tag_ids = apply_discogs_tag_hints(
                            session, DEFAULT_USER_ID, ingest_result.tag_hints
                        )
                        return SearchResponse(
                            status="created",
                            release=_release_response(release),
                            suggested_tag_ids=[t.value for t in tag_ids],
                        )
                    case AlreadyExists(value=release):
                        tag_ids = apply_discogs_tag_hints(
                            session, DEFAULT_USER_ID, ingest_result.tag_hints
                        )
                        return SearchResponse(
                            status="already_exists",
                            release=_release_response(release),
                            suggested_tag_ids=[t.value for t in tag_ids],
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
            case Ok(value=ingest_result):
                match ingest_result.outcome:
                    case Created(value=release):
                        save_release(session, release)
                        tag_ids = apply_discogs_tag_hints(
                            session, DEFAULT_USER_ID, ingest_result.tag_hints
                        )
                        return SearchResponse(
                            status="created",
                            release=_release_response(release),
                            suggested_tag_ids=[t.value for t in tag_ids],
                        )
                    case AlreadyExists(value=release):
                        tag_ids = apply_discogs_tag_hints(
                            session, DEFAULT_USER_ID, ingest_result.tag_hints
                        )
                        return SearchResponse(
                            status="already_exists",
                            release=_release_response(release),
                            suggested_tag_ids=[t.value for t in tag_ids],
                        )
                    case AmbiguousMatch(candidates=candidates):
                        return SearchResponse(
                            status="ambiguous",
                            candidates=[_candidate_response(c) for c in candidates],
                        )
                    case NotFound():
                        return SearchResponse(status="not_found")


@app.get("/releases/{release_id}", response_model=ReleaseDetailResponse)
def get_release(release_id: int, http_request: Request) -> ReleaseDetailResponse:
    engine = http_request.app.state.engine
    with Session(engine) as session:
        release = lookup_existing_release(session, ReleaseId(release_id))
        if release is None:
            raise HTTPException(status_code=404, detail="Release not found")
        return _release_detail_response(release)


@app.patch("/releases/{release_id}", response_model=ReleaseDetailResponse)
def edit_release(
    release_id: int, body: ReleaseEditRequest, http_request: Request
) -> ReleaseDetailResponse:
    engine = http_request.app.state.engine
    with Session(engine) as session:
        release = lookup_existing_release(session, ReleaseId(release_id))
        if release is None:
            raise HTTPException(status_code=404, detail="Release not found")
        match _apply_release_edit(release, body):
            case Err(error=message):
                raise HTTPException(status_code=400, detail=message)
            case Ok(value=updated):
                update_release(session, updated)
                return _release_detail_response(updated)


@app.get("/tags", response_model=list[TagCategoryResponse])
def list_tags_endpoint(http_request: Request) -> list[TagCategoryResponse]:
    engine = http_request.app.state.engine
    with Session(engine) as session:
        return [
            TagCategoryResponse(
                id=category.id.value,
                name=category.name,
                tags=[
                    TagResponse(id=tag.id.value, name=tag.name)
                    for tag in list_tags(session, DEFAULT_USER_ID, category.id)
                ],
            )
            for category in list_tag_categories(session, DEFAULT_USER_ID)
        ]


@app.post("/tags", response_model=TagResponse)
def create_tag(body: CreateTagRequest, http_request: Request) -> TagResponse:
    engine = http_request.app.state.engine
    with Session(engine) as session:
        category = get_or_create_tag_category(session, DEFAULT_USER_ID, body.category)
        tag = get_or_create_tag(session, DEFAULT_USER_ID, category.id, body.name)
        session.commit()
        return TagResponse(id=tag.id.value, name=tag.name)


@app.post("/collection-items", response_model=CollectionItemResponse)
def create_collection_item(
    body: CreateCollectionItemRequest, http_request: Request
) -> CollectionItemResponse:
    engine = http_request.app.state.engine
    with Session(engine) as session:
        release_id = ReleaseId(body.release_id)
        if lookup_existing_release(session, release_id) is None:
            raise HTTPException(status_code=404, detail="Release not found")
        item = CollectionItem(
            user_id=DEFAULT_USER_ID,
            release_id=release_id,
            condition=body.condition,
            notes=body.notes,
            date_added=datetime.now(UTC),
            tag_ids=frozenset(TagId(tag_id) for tag_id in body.tag_ids),
        )
        save_collection_item(session, item)
        return _collection_item_response(item)
