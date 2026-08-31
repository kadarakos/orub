"""User-specific entities. See design doc §3 User-specific entities.

Every type here is scoped to a single user (§5): TagCategory and Tag are
user-defined vocabulary, CollectionItem is "this user owns this release",
and Edge is a directed "track A can follow track B" relationship. None of
these carry SQLAlchemy or FastAPI concerns -- persistence-level user
scoping (the `WHERE user_id = ...` repository pattern) is a §4.3 concern,
not a domain one.
"""

from __future__ import annotations

from datetime import datetime

import attrs

from orub.domain.identity import ReleaseId, TagCategoryId, TagId, TrackId, UserId
from orub.domain.sums import Condition, EdgeSource

# No auth yet (design doc §4.5, deferred) -- CLI and API both operate as this
# single implicit user, same tolerance already applied to CORS/session
# handling elsewhere. Revisit once real accounts exist.
DEFAULT_USER_ID = UserId(1)


@attrs.frozen(slots=True)
class TagCategory:
    id: TagCategoryId
    user_id: UserId
    name: str


@attrs.frozen(slots=True)
class Tag:
    id: TagId
    user_id: UserId
    category_id: TagCategoryId
    name: str


@attrs.frozen(slots=True)
class CollectionItem:
    user_id: UserId
    release_id: ReleaseId
    condition: Condition
    notes: str
    date_added: datetime
    tag_ids: frozenset[TagId] = attrs.field(factory=frozenset[TagId])


@attrs.frozen(slots=True)
class Edge:
    from_track_id: TrackId
    to_track_id: TrackId
    source: EdgeSource
    user_id: UserId
    created_at: datetime
    weight: float | None = None
