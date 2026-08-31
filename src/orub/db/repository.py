"""Catalog repository functions. See design doc §4.3.

Catalog entities (Release/Track) aren't user-owned, so there's no
`user_id` scoping here -- that only applies to the user-specific tables in
TODO.md's later Phase 3 slice (CollectionItem/Tag/Edge). Callers adapt
`existing_release` into the `ExistingRelease` callable shape (see
`orub.discogs.ingest`) by partially applying the session, e.g. in cli.py.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from orub.db.mapping import release_from_row, release_to_row
from orub.db.models import ReleaseRow
from orub.domain.catalog import Release
from orub.domain.identity import ReleaseId


def existing_release(session: Session, release_id: ReleaseId) -> Release | None:
    row = session.get(ReleaseRow, release_id.value)
    return release_from_row(row) if row is not None else None


def save_release(session: Session, release: Release) -> None:
    session.add(release_to_row(release))
    session.commit()


def update_release(session: Session, release: Release) -> None:
    """Overwrite an existing release (and its tracklist) in place.

    Uses `merge` rather than `add` so it upserts by primary key: existing
    `TrackRow`s are updated, tracks no longer in `release.tracklist` are
    dropped via `delete-orphan` cascade, and new ones are inserted.
    """
    session.merge(release_to_row(release))
    session.commit()
