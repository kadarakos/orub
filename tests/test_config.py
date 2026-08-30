import pathlib

import pytest

from orub.config import Settings


def test_settings_reads_discogs_token_from_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    # Run from an empty directory so the repo's real .env (with a real
    # token) isn't picked up -- we want to test env-var reading in isolation.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DISCOGS_TOKEN", "abc123")
    monkeypatch.delenv("DISCOGS_USER_AGENT", raising=False)

    # pydantic-settings sources required fields from the environment at
    # runtime, which pyright's dataclass-transform-based constructor
    # signature can't see statically.
    settings = Settings()  # type: ignore[call-arg]

    assert settings.discogs_token == "abc123"
    assert settings.discogs_user_agent == "orub/0.1"


def test_settings_reads_discogs_user_agent_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DISCOGS_TOKEN", "abc123")
    monkeypatch.setenv("DISCOGS_USER_AGENT", "custom-agent/1.0")

    settings = Settings()  # type: ignore[call-arg]

    assert settings.discogs_user_agent == "custom-agent/1.0"
