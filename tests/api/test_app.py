import pathlib
from collections.abc import Generator

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from orub.api.app import app

_RELEASE_JSON = {
    "id": 249504,
    "title": "Never Gonna Give You Up",
    "artists": [{"id": 72872, "name": "Rick Astley"}],
    "labels": [{"id": 895, "name": "RCA"}],
    "year": 1987,
    "formats": [{"name": "Vinyl"}],
    "tracklist": [],
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

_OTHER_SEARCH_RESULT_JSON = {
    "id": 5453130,
    "title": "Rick Astley - Never Gonna Give You Up",
    "year": "1987",
    "country": "US",
    "label": ["RCA"],
    "format": ["Vinyl", '7"', "45 RPM"],
    "catno": "5347-7-RAA",
}


@pytest.fixture(autouse=True)
def _isolated_settings(  # pyright: ignore[reportUnusedFunction]
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DISCOGS_TOKEN", "fake-token")


@pytest.fixture
def client() -> Generator[TestClient]:  # pyright: ignore[reportUnusedFunction]
    with TestClient(app) as client:
        yield client


@respx.mock
def test_search_reports_created(client: TestClient) -> None:
    respx.get("https://api.discogs.com/database/search").mock(
        return_value=httpx.Response(200, json={"results": [_SEARCH_RESULT_JSON]})
    )
    respx.get("https://api.discogs.com/releases/249504").mock(
        return_value=httpx.Response(200, json=_RELEASE_JSON)
    )

    response = client.post(
        "/releases/search",
        json={"release_title": "Never Gonna Give You Up", "artist": "Rick Astley"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "created"
    assert body["release"]["id"] == 249504
    assert body["release"]["title"] == "Never Gonna Give You Up"


@respx.mock
def test_search_reports_already_exists_on_second_call(client: TestClient) -> None:
    respx.get("https://api.discogs.com/database/search").mock(
        return_value=httpx.Response(200, json={"results": [_SEARCH_RESULT_JSON]})
    )
    respx.get("https://api.discogs.com/releases/249504").mock(
        return_value=httpx.Response(200, json=_RELEASE_JSON)
    )
    payload = {"release_title": "Never Gonna Give You Up", "artist": "Rick Astley"}

    first = client.post("/releases/search", json=payload)
    second = client.post("/releases/search", json=payload)

    assert first.json()["status"] == "created"
    assert second.json()["status"] == "already_exists"
    assert second.json()["release"]["id"] == 249504


@respx.mock
def test_search_reports_ambiguous_match(client: TestClient) -> None:
    respx.get("https://api.discogs.com/database/search").mock(
        return_value=httpx.Response(
            200, json={"results": [_SEARCH_RESULT_JSON, _OTHER_SEARCH_RESULT_JSON]}
        )
    )

    response = client.post("/releases/search", json={"release_title": "Never Gonna Give You Up"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ambiguous"
    assert [c["id"] for c in body["candidates"]] == [249504, 5453130]


@respx.mock
def test_search_reports_not_found(client: TestClient) -> None:
    respx.get("https://api.discogs.com/database/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    response = client.post("/releases/search", json={"release_title": "asdkjaslkdj999"})

    assert response.status_code == 200
    assert response.json() == {"status": "not_found", "release": None, "candidates": None}


@respx.mock
def test_search_reports_network_error_as_bad_gateway(client: TestClient) -> None:
    respx.get("https://api.discogs.com/database/search").mock(return_value=httpx.Response(500))

    response = client.post("/releases/search", json={"release_title": "Never Gonna Give You Up"})

    assert response.status_code == 502
    assert "Network error" in response.json()["detail"]


@respx.mock
def test_search_reports_rate_limited(client: TestClient) -> None:
    respx.get("https://api.discogs.com/database/search").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "30"})
    )

    response = client.post("/releases/search", json={"release_title": "Never Gonna Give You Up"})

    assert response.status_code == 429
    assert "30.0" in response.json()["detail"]


@respx.mock
def test_ingest_reports_created_then_already_exists(client: TestClient) -> None:
    respx.get("https://api.discogs.com/releases/249504").mock(
        return_value=httpx.Response(200, json=_RELEASE_JSON)
    )

    first = client.post("/releases/249504/ingest")
    second = client.post("/releases/249504/ingest")

    assert first.status_code == 200
    assert first.json()["status"] == "created"
    assert first.json()["release"]["id"] == 249504
    assert second.json()["status"] == "already_exists"
    assert second.json()["release"]["id"] == 249504


@respx.mock
def test_ingest_reports_not_found(client: TestClient) -> None:
    respx.get("https://api.discogs.com/releases/999999999").mock(return_value=httpx.Response(404))

    response = client.post("/releases/999999999/ingest")

    assert response.status_code == 200
    assert response.json() == {"status": "not_found", "release": None, "candidates": None}
