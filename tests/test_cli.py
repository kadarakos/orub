import pathlib

import httpx
import pytest
import respx
from typer.testing import CliRunner

from orub.cli import app

runner = CliRunner()

_RELEASE_JSON = {
    "id": 249504,
    "title": "Never Gonna Give You Up",
    "artists": [{"id": 72872, "name": "Rick Astley"}],
    "labels": [{"id": 895, "name": "RCA", "catno": "PB 41447"}],
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


@respx.mock
def test_ingest_release_reports_created() -> None:
    respx.get("https://api.discogs.com/releases/249504").mock(
        return_value=httpx.Response(200, json=_RELEASE_JSON)
    )

    result = runner.invoke(app, ["ingest-release", "249504"])

    assert result.exit_code == 0
    assert "Created: Never Gonna Give You Up" in result.stdout
    assert "catno=PB 41447" in result.stdout


@respx.mock
def test_ingest_release_reports_already_exists_on_second_run() -> None:
    respx.get("https://api.discogs.com/releases/249504").mock(
        return_value=httpx.Response(200, json=_RELEASE_JSON)
    )

    first = runner.invoke(app, ["ingest-release", "249504"])
    second = runner.invoke(app, ["ingest-release", "249504"])

    assert first.exit_code == 0
    assert "Created: Never Gonna Give You Up" in first.stdout
    assert second.exit_code == 0
    assert "Already exists: Never Gonna Give You Up" in second.stdout


@respx.mock
def test_ingest_release_reports_not_found() -> None:
    respx.get("https://api.discogs.com/releases/999999").mock(return_value=httpx.Response(404))

    result = runner.invoke(app, ["ingest-release", "999999"])

    assert result.exit_code == 0
    assert "Not found: release 999999" in result.stdout


@respx.mock
def test_ingest_release_reports_network_error_with_nonzero_exit() -> None:
    respx.get("https://api.discogs.com/releases/249504").mock(return_value=httpx.Response(500))

    result = runner.invoke(app, ["ingest-release", "249504"])

    assert result.exit_code == 1
    assert "Network error" in result.stdout


@respx.mock
def test_ingest_release_reports_rate_limited_with_nonzero_exit() -> None:
    respx.get("https://api.discogs.com/releases/249504").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "30"})
    )

    result = runner.invoke(app, ["ingest-release", "249504"])

    assert result.exit_code == 1
    assert "Rate limited (retry after 30.0s)" in result.stdout


@respx.mock
def test_ingest_release_reports_malformed_response_with_nonzero_exit() -> None:
    respx.get("https://api.discogs.com/releases/249504").mock(
        return_value=httpx.Response(200, json={"unexpected": "shape"})
    )

    result = runner.invoke(app, ["ingest-release", "249504"])

    assert result.exit_code == 1
    assert "Malformed response" in result.stdout


@respx.mock
def test_search_release_ingests_unique_match() -> None:
    respx.get("https://api.discogs.com/database/search").mock(
        return_value=httpx.Response(200, json={"results": [_SEARCH_RESULT_JSON]})
    )
    respx.get("https://api.discogs.com/releases/249504").mock(
        return_value=httpx.Response(200, json=_RELEASE_JSON)
    )

    result = runner.invoke(
        app,
        ["search-release", "--release-title", "Never Gonna Give You Up", "--artist", "Rick Astley"],
    )

    assert result.exit_code == 0
    assert "Created: Never Gonna Give You Up" in result.stdout


@respx.mock
def test_search_release_forwards_catno_option() -> None:
    route = respx.get("https://api.discogs.com/database/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    runner.invoke(app, ["search-release", "--catno", "BOO006"])

    assert route.calls.last.request.url.params["catno"] == "BOO006"


@respx.mock
def test_search_release_reports_already_exists_on_second_run() -> None:
    respx.get("https://api.discogs.com/database/search").mock(
        return_value=httpx.Response(200, json={"results": [_SEARCH_RESULT_JSON]})
    )
    respx.get("https://api.discogs.com/releases/249504").mock(
        return_value=httpx.Response(200, json=_RELEASE_JSON)
    )
    args = [
        "search-release",
        "--release-title",
        "Never Gonna Give You Up",
        "--artist",
        "Rick Astley",
    ]

    first = runner.invoke(app, args)
    second = runner.invoke(app, args)

    assert first.exit_code == 0
    assert "Created: Never Gonna Give You Up" in first.stdout
    assert second.exit_code == 0
    assert "Already exists: Never Gonna Give You Up" in second.stdout


@respx.mock
def test_search_release_lists_candidates_on_ambiguous_match() -> None:
    respx.get("https://api.discogs.com/database/search").mock(
        return_value=httpx.Response(
            200, json={"results": [_SEARCH_RESULT_JSON, _OTHER_SEARCH_RESULT_JSON]}
        )
    )

    result = runner.invoke(app, ["search-release", "--release-title", "Never Gonna Give You Up"])

    assert result.exit_code == 0
    assert "2 matches" in result.stdout
    assert "[id=249504]" in result.stdout
    assert "[id=5453130]" in result.stdout


@respx.mock
def test_search_release_reports_no_matches() -> None:
    respx.get("https://api.discogs.com/database/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    result = runner.invoke(app, ["search-release", "--release-title", "asdkjaslkdj999"])

    assert result.exit_code == 0
    assert "No matches found" in result.stdout


@respx.mock
def test_search_release_reports_network_error_with_nonzero_exit() -> None:
    respx.get("https://api.discogs.com/database/search").mock(return_value=httpx.Response(500))

    result = runner.invoke(app, ["search-release", "--release-title", "Never Gonna Give You Up"])

    assert result.exit_code == 1
    assert "Network error" in result.stdout
