"""Gateway-level errors for the Discogs client. See design doc §4.2, §8.

These are infrastructure-level failures (network, rate limiting, unexpected
response shape) -- distinct from IngestOutcome, which models the *domain*
result of a clean fetch (found / not found / already have it / ambiguous).
A 404 from Discogs is not one of these; it's a legitimate "not found"
answer, so it flows through as `Ok(None)` from the client, not an Err here.
"""

from __future__ import annotations

import attrs


@attrs.frozen(slots=True)
class NetworkError:
    message: str


@attrs.frozen(slots=True)
class RateLimited:
    retry_after_seconds: float | None = None


@attrs.frozen(slots=True)
class MalformedResponse:
    message: str


type FetchError = NetworkError | RateLimited | MalformedResponse
