import httpx
import respx

from orub.discogs.client import DiscogsClient
from orub.discogs.errors import MalformedResponse, NetworkError, RateLimited
from orub.discogs.models import DiscogsReleaseDTO, DiscogsSearchResultDTO
from orub.domain.identity import ReleaseId
from orub.domain.result import Err, Ok

_RELEASE_JSON = {
    "id": 249504,
    "title": "Never Gonna Give You Up",
    "artists": [{"id": 72872, "name": "Rick Astley"}],
    "labels": [{"id": 895, "name": "RCA"}],
    "year": 1987,
    "formats": [{"name": "Vinyl"}],
    "tracklist": [{"position": "A", "title": "Never Gonna Give You Up"}],
}

_SEARCH_RESULT_JSON = {
    "id": 249504,
    "title": "Rick Astley - Never Gonna Give You Up",
    "year": "1987",
    "country": "Europe",
    "label": ["RCA"],
    "format": ["Vinyl", '12"', "45 RPM"],
    "catno": "PB 41447",
}


@respx.mock
def test_fetch_release_returns_ok_dto_on_200() -> None:
    respx.get("https://api.discogs.com/releases/249504").mock(
        return_value=httpx.Response(200, json=_RELEASE_JSON)
    )
    client = DiscogsClient(token="fake-token", user_agent="orub-test/0.1")

    result = client.fetch_release(ReleaseId(249504))

    assert isinstance(result, Ok)
    assert isinstance(result.value, DiscogsReleaseDTO)
    assert result.value.id == 249504


@respx.mock
def test_fetch_release_sends_auth_header() -> None:
    route = respx.get("https://api.discogs.com/releases/249504").mock(
        return_value=httpx.Response(200, json=_RELEASE_JSON)
    )
    client = DiscogsClient(token="fake-token", user_agent="orub-test/0.1")

    client.fetch_release(ReleaseId(249504))

    assert route.calls.last.request.headers["Authorization"] == "Discogs token=fake-token"


@respx.mock
def test_fetch_release_returns_ok_none_on_404() -> None:
    respx.get("https://api.discogs.com/releases/999999").mock(return_value=httpx.Response(404))
    client = DiscogsClient(token="fake-token", user_agent="orub-test/0.1")

    result = client.fetch_release(ReleaseId(999999))

    assert result == Ok(None)


@respx.mock
def test_fetch_release_returns_rate_limited_on_429() -> None:
    respx.get("https://api.discogs.com/releases/249504").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "30"})
    )
    client = DiscogsClient(token="fake-token", user_agent="orub-test/0.1")

    result = client.fetch_release(ReleaseId(249504))

    assert result == Err(RateLimited(retry_after_seconds=30.0))


@respx.mock
def test_fetch_release_returns_network_error_on_connection_failure() -> None:
    respx.get("https://api.discogs.com/releases/249504").mock(
        side_effect=httpx.ConnectError("boom")
    )
    client = DiscogsClient(token="fake-token", user_agent="orub-test/0.1")

    result = client.fetch_release(ReleaseId(249504))

    assert isinstance(result, Err)
    assert isinstance(result.error, NetworkError)


@respx.mock
def test_fetch_release_returns_malformed_response_on_bad_shape() -> None:
    respx.get("https://api.discogs.com/releases/249504").mock(
        return_value=httpx.Response(200, json={"unexpected": "shape"})
    )
    client = DiscogsClient(token="fake-token", user_agent="orub-test/0.1")

    result = client.fetch_release(ReleaseId(249504))

    assert isinstance(result, Err)
    assert isinstance(result.error, MalformedResponse)


@respx.mock
def test_fetch_release_returns_network_error_on_server_error() -> None:
    respx.get("https://api.discogs.com/releases/249504").mock(return_value=httpx.Response(500))
    client = DiscogsClient(token="fake-token", user_agent="orub-test/0.1")

    result = client.fetch_release(ReleaseId(249504))

    assert isinstance(result, Err)
    assert isinstance(result.error, NetworkError)


@respx.mock
def test_client_context_manager_returns_a_usable_client() -> None:
    respx.get("https://api.discogs.com/releases/249504").mock(
        return_value=httpx.Response(200, json=_RELEASE_JSON)
    )

    with DiscogsClient(token="fake-token", user_agent="orub-test/0.1") as client:
        result = client.fetch_release(ReleaseId(249504))

    assert isinstance(result, Ok)


def test_client_close_does_not_raise() -> None:
    client = DiscogsClient(token="fake-token", user_agent="orub-test/0.1")
    client.close()


@respx.mock
def test_search_releases_returns_ok_tuple_of_dtos_on_200() -> None:
    respx.get("https://api.discogs.com/database/search").mock(
        return_value=httpx.Response(200, json={"results": [_SEARCH_RESULT_JSON]})
    )
    client = DiscogsClient(token="fake-token", user_agent="orub-test/0.1")

    result = client.search_releases(release_title="Never Gonna Give You Up", artist="Rick Astley")

    assert isinstance(result, Ok)
    assert result.value == (DiscogsSearchResultDTO.model_validate(_SEARCH_RESULT_JSON),)


@respx.mock
def test_search_releases_sends_query_params() -> None:
    route = respx.get("https://api.discogs.com/database/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    client = DiscogsClient(token="fake-token", user_agent="orub-test/0.1")

    client.search_releases(
        release_title="Never Gonna Give You Up",
        track_title="Never Gonna Give You Up",
        artist="Rick Astley",
        label="RCA",
        year=1987,
    )

    sent = route.calls.last.request.url.params
    assert sent["type"] == "release"
    assert sent["release_title"] == "Never Gonna Give You Up"
    assert sent["track"] == "Never Gonna Give You Up"
    assert sent["artist"] == "Rick Astley"
    assert sent["label"] == "RCA"
    assert sent["year"] == "1987"


@respx.mock
def test_search_releases_returns_ok_empty_tuple_on_no_matches() -> None:
    respx.get("https://api.discogs.com/database/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    client = DiscogsClient(token="fake-token", user_agent="orub-test/0.1")

    result = client.search_releases(release_title="asdkjaslkdjaslkdjalskdjalskdj999")

    assert result == Ok(())


@respx.mock
def test_search_releases_returns_rate_limited_on_429() -> None:
    respx.get("https://api.discogs.com/database/search").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "30"})
    )
    client = DiscogsClient(token="fake-token", user_agent="orub-test/0.1")

    result = client.search_releases(release_title="Never Gonna Give You Up")

    assert result == Err(RateLimited(retry_after_seconds=30.0))


@respx.mock
def test_search_releases_returns_network_error_on_connection_failure() -> None:
    respx.get("https://api.discogs.com/database/search").mock(
        side_effect=httpx.ConnectError("boom")
    )
    client = DiscogsClient(token="fake-token", user_agent="orub-test/0.1")

    result = client.search_releases(release_title="Never Gonna Give You Up")

    assert isinstance(result, Err)
    assert isinstance(result.error, NetworkError)


@respx.mock
def test_search_releases_returns_network_error_on_server_error() -> None:
    respx.get("https://api.discogs.com/database/search").mock(return_value=httpx.Response(500))
    client = DiscogsClient(token="fake-token", user_agent="orub-test/0.1")

    result = client.search_releases(release_title="Never Gonna Give You Up")

    assert isinstance(result, Err)
    assert isinstance(result.error, NetworkError)


@respx.mock
def test_search_releases_returns_malformed_response_on_bad_shape() -> None:
    respx.get("https://api.discogs.com/database/search").mock(
        return_value=httpx.Response(200, json={"unexpected": "shape"})
    )
    client = DiscogsClient(token="fake-token", user_agent="orub-test/0.1")

    result = client.search_releases(release_title="Never Gonna Give You Up")

    assert isinstance(result, Err)
    assert isinstance(result.error, MalformedResponse)
