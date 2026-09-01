"""Discogs HTTP client. See design doc §4.2, §8 (rate limit handling).

This is the impure edge: the only place in the ingestion pipeline that
does network I/O. It hands back a Result so callers never need to catch
exceptions for expected failure modes (network errors, 404s, rate
limiting, malformed responses).

Rate limiting is currently reactive, not proactive: Discogs returns 429
when you exceed the limit, and we surface that as `Err(RateLimited(...))`
rather than tracking request timing client-side. Revisit with proactive
throttling/backoff once we do bulk operations (e.g. a full collection
sync) where hitting the limit repeatedly would be wasteful.
"""

from __future__ import annotations

from typing import Self

import httpx
import pydantic

from orub.discogs.errors import FetchError, MalformedResponse, NetworkError, RateLimited
from orub.discogs.models import DiscogsReleaseDTO, DiscogsSearchResponseDTO, DiscogsSearchResultDTO
from orub.domain.identity import ReleaseId
from orub.domain.result import Err, Ok, Result

DISCOGS_API_BASE = "https://api.discogs.com"


def _status_error(response: httpx.Response) -> FetchError | None:
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        return RateLimited(retry_after_seconds=float(retry_after) if retry_after else None)
    if response.status_code >= 400:
        return NetworkError(f"Discogs returned HTTP {response.status_code}")
    return None


class DiscogsClient:
    def __init__(self, token: str, user_agent: str) -> None:
        self._http = httpx.Client(
            base_url=DISCOGS_API_BASE,
            headers={
                "User-Agent": user_agent,
                "Authorization": f"Discogs token={token}",
            },
        )

    def _get(
        self, path: str, params: dict[str, str] | None = None
    ) -> Result[httpx.Response, FetchError]:
        try:
            return Ok(self._http.get(path, params=params))
        except httpx.HTTPError as exc:
            return Err(NetworkError(str(exc)))

    def fetch_release(self, release_id: ReleaseId) -> Result[DiscogsReleaseDTO | None, FetchError]:
        match self._get(f"/releases/{release_id.value}"):
            case Err() as err:
                return err
            case Ok(value=response):
                if response.status_code == 404:
                    return Ok(None)
                if (error := _status_error(response)) is not None:
                    return Err(error)
                try:
                    return Ok(DiscogsReleaseDTO.model_validate(response.json()))
                except (ValueError, pydantic.ValidationError) as exc:
                    return Err(MalformedResponse(str(exc)))

    def search_releases(
        self,
        *,
        release_title: str | None = None,
        track_title: str | None = None,
        artist: str | None = None,
        label: str | None = None,
        year: int | None = None,
        catno: str | None = None,
    ) -> Result[tuple[DiscogsSearchResultDTO, ...], FetchError]:
        params: dict[str, str] = {"type": "release"}
        if release_title is not None:
            params["release_title"] = release_title
        if track_title is not None:
            params["track"] = track_title
        if artist is not None:
            params["artist"] = artist
        if label is not None:
            params["label"] = label
        if year is not None:
            params["year"] = str(year)
        if catno is not None:
            params["catno"] = catno

        match self._get("/database/search", params=params):
            case Err() as err:
                return err
            case Ok(value=response):
                if (error := _status_error(response)) is not None:
                    return Err(error)
                try:
                    parsed = DiscogsSearchResponseDTO.model_validate(response.json())
                except (ValueError, pydantic.ValidationError) as exc:
                    return Err(MalformedResponse(str(exc)))
                return Ok(tuple(parsed.results))

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
