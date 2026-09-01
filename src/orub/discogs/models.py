"""Pydantic DTOs for the subset of the Discogs release JSON shape we use.

See design doc §2 ("pydantic is used only where untrusted data enters the
system") and §4.2. Only the fields the mapping layer actually needs are
modeled -- Discogs release responses have many more fields we don't care
about; pydantic ignores unknown fields by default, which is what we want.
"""

from __future__ import annotations

from pydantic import BaseModel


class DiscogsArtistDTO(BaseModel):
    id: int
    name: str


class DiscogsLabelDTO(BaseModel):
    id: int
    name: str
    catno: str | None = None


class DiscogsFormatDTO(BaseModel):
    name: str
    descriptions: list[str] = []


class DiscogsTrackDTO(BaseModel):
    position: str
    title: str
    type: str = "track"
    artists: list[DiscogsArtistDTO] | None = None


class DiscogsReleaseDTO(BaseModel):
    id: int
    title: str
    artists: list[DiscogsArtistDTO]
    labels: list[DiscogsLabelDTO]
    year: int | None = None
    formats: list[DiscogsFormatDTO]
    tracklist: list[DiscogsTrackDTO]
    genres: list[str] = []
    styles: list[str] = []


class DiscogsSearchResultDTO(BaseModel):
    """One `/database/search` hit.

    This is a distinct, thinner shape from `DiscogsReleaseDTO` -- `title` is
    a combined "Artist - Title" string, and `label`/`format` are denormalized
    name lists with no ids. We only model the fields useful for a human to
    tell candidates apart (catno, country, label, format); the full release
    is fetched by id via `DiscogsClient.fetch_release` once one is picked.
    """

    id: int
    title: str
    year: int | None = None
    country: str | None = None
    label: list[str] = []
    format: list[str] = []
    catno: str | None = None


class DiscogsSearchResponseDTO(BaseModel):
    results: list[DiscogsSearchResultDTO]
