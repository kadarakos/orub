"""Identity types. See design doc §3 Identity.

ArtistId, LabelId, ReleaseId are sourced from Discogs' own IDs (Discogs is
the source of truth for these entities). TrackId is minted by us, since
Discogs does not give tracks stable IDs -- they're positions like "A1",
"B2" within a release. We key a track by (release_id, position); if
position edits ever need to not break identity, revisit with a UUID.

UserId, TagCategoryId, and TagId aren't from Discogs -- design doc §3 lists
them implicitly via user-specific entities (§3 User-specific entities) but
doesn't name their id types. Minted by us; kept as plain wrappers here
since how they're generated (DB autoincrement vs. UUID) is a persistence
concern (§8), not a domain one.
"""

from __future__ import annotations

import attrs


@attrs.frozen(slots=True)
class ArtistId:
    value: int


@attrs.frozen(slots=True)
class LabelId:
    value: int


@attrs.frozen(slots=True)
class ReleaseId:
    value: int


@attrs.frozen(slots=True)
class TrackPosition:
    value: str


@attrs.frozen(slots=True)
class TrackId:
    release_id: ReleaseId
    position: TrackPosition


@attrs.frozen(slots=True)
class UserId:
    value: int


@attrs.frozen(slots=True)
class TagCategoryId:
    value: int


@attrs.frozen(slots=True)
class TagId:
    value: int
