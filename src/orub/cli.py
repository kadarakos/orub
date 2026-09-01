"""Typer CLI. See design doc §8: exercise ingestion/graph logic without a UI.

`ingest-release` and `search-release` wire the real `DiscogsClient` and a
SQLite-backed `Session` (design doc §4.3) to the ingestion pipeline:
`existing_release` is a real DB lookup, and a `Created` outcome is persisted
before it's reported, so a second run of the same id/search now reports
`AlreadyExists`.
"""

from __future__ import annotations

import typer
from sqlalchemy.orm import Session

from orub.config import Settings
from orub.db.repository import existing_release as lookup_existing_release
from orub.db.repository import save_release
from orub.db.session import make_engine
from orub.db.tags import apply_discogs_tag_hints
from orub.discogs.client import DiscogsClient
from orub.discogs.errors import FetchError, MalformedResponse, NetworkError, RateLimited
from orub.discogs.ingest import ReleaseSearchQuery, ingest_release_by_id, ingest_release_by_search
from orub.discogs.models import DiscogsSearchResultDTO
from orub.domain.catalog import Release
from orub.domain.identity import ReleaseId
from orub.domain.ingest_outcome import AlreadyExists, AmbiguousMatch, Created, NotFound
from orub.domain.result import Err, Ok, Result
from orub.domain.user import DEFAULT_USER_ID

app = typer.Typer()


@app.callback()
def _callback() -> None:  # pyright: ignore[reportUnusedFunction]
    """orub: personal vinyl collection tracker."""


def _open_session(settings: Settings) -> Session:
    return Session(make_engine(settings.database_url))


def _describe_release(release: Release) -> str:
    year = release.year if release.year is not None else "?"
    catno = f", catno={release.catno}" if release.catno is not None else ""
    return f"{release.title} ({year}, {release.format.value}{catno}) [id={release.id.value}]"


def _describe_candidate(candidate: DiscogsSearchResultDTO) -> str:
    year = candidate.year if candidate.year is not None else "?"
    label = ", ".join(candidate.label) or "unknown label"
    fmt = ", ".join(candidate.format) or "unknown format"
    catno = f", catno={candidate.catno}" if candidate.catno is not None else ""
    return f"{candidate.title} ({year}, {fmt}, {label}{catno}) [id={candidate.id}]"


def _echo_fetch_error(error: FetchError) -> None:
    match error:
        case NetworkError(message=message):
            typer.echo(f"Network error: {message}")
        case RateLimited(retry_after_seconds=retry_after):
            typer.echo(f"Rate limited (retry after {retry_after}s)")
        case MalformedResponse(message=message):
            typer.echo(f"Malformed response: {message}")


@app.command("ingest-release")
def ingest_release(release_id: int) -> None:
    """Fetch a Discogs release by id and report what ingesting it would do."""
    settings = Settings()  # type: ignore[call-arg]

    with (
        DiscogsClient(
            token=settings.discogs_token, user_agent=settings.discogs_user_agent
        ) as client,
        _open_session(settings) as session,
    ):
        result = ingest_release_by_id(
            fetch_release=client.fetch_release,
            existing_release=lambda rid: lookup_existing_release(session, rid),
            release_id=ReleaseId(release_id),
        )

        match result:
            case Err(error=error):
                _echo_fetch_error(error)
                raise typer.Exit(code=1)
            case Ok(value=ingest_result):
                match ingest_result.outcome:
                    case Created(value=release):
                        save_release(session, release)
                        apply_discogs_tag_hints(session, DEFAULT_USER_ID, ingest_result.tag_hints)
                        typer.echo(f"Created: {_describe_release(release)}")
                    case AlreadyExists(value=release):
                        apply_discogs_tag_hints(session, DEFAULT_USER_ID, ingest_result.tag_hints)
                        typer.echo(f"Already exists: {_describe_release(release)}")
                    case AmbiguousMatch():
                        typer.echo("Ambiguous match")
                    case NotFound():
                        typer.echo(f"Not found: release {release_id}")


@app.command("search-release")
def search_release(
    release_title: str | None = None,
    track_title: str | None = None,
    artist: str | None = None,
    label: str | None = None,
    year: int | None = None,
    catno: str | None = None,
) -> None:
    """Search Discogs and ingest the full release on a unique match.

    On an ambiguous match, lists candidates and their ids -- rerun with
    `ingest-release <id>` to ingest one of them.
    """
    settings = Settings()  # type: ignore[call-arg]
    query = ReleaseSearchQuery(
        release_title=release_title,
        track_title=track_title,
        artist=artist,
        label=label,
        year=year,
        catno=catno,
    )

    with (
        DiscogsClient(
            token=settings.discogs_token, user_agent=settings.discogs_user_agent
        ) as client,
        _open_session(settings) as session,
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
                catno=query.catno,
            )

        result = ingest_release_by_search(
            search=_search,
            fetch_release=client.fetch_release,
            existing_release=lambda rid: lookup_existing_release(session, rid),
            query=query,
        )

        match result:
            case Err(error=error):
                _echo_fetch_error(error)
                raise typer.Exit(code=1)
            case Ok(value=ingest_result):
                match ingest_result.outcome:
                    case Created(value=release):
                        save_release(session, release)
                        apply_discogs_tag_hints(session, DEFAULT_USER_ID, ingest_result.tag_hints)
                        typer.echo(f"Created: {_describe_release(release)}")
                    case AlreadyExists(value=release):
                        apply_discogs_tag_hints(session, DEFAULT_USER_ID, ingest_result.tag_hints)
                        typer.echo(f"Already exists: {_describe_release(release)}")
                    case AmbiguousMatch(candidates=candidates):
                        typer.echo(
                            f"{len(candidates)} matches, pick one and run `ingest-release <id>`:"
                        )
                        for candidate in candidates:
                            typer.echo(f"  {_describe_candidate(candidate)}")
                    case NotFound():
                        typer.echo("No matches found")


if __name__ == "__main__":
    app()
