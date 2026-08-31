"""CollectionItem repository functions. See design doc §4.3, TODO.md Phase 3.

User-owned, scoped by a hardcoded `user_id` argument (no real auth yet --
see `orub.domain.user.DEFAULT_USER_ID`). A `CollectionItem` has no id of its
own in the domain -- it's identified by the `(user_id, release_id)` pair --
so `save_collection_item` looks up any existing row's surrogate id first and
carries it over, making `merge` upsert by that pair instead of inserting a
duplicate.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Session

from orub.db.mapping import collection_item_from_row, collection_item_to_row
from orub.db.models import CollectionItemRow
from orub.domain.identity import ReleaseId
from orub.domain.user import CollectionItem, UserId


def existing_collection_item(
    session: Session, user_id: UserId, release_id: ReleaseId
) -> CollectionItem | None:
    row = session.scalar(
        sa.select(CollectionItemRow).where(
            CollectionItemRow.user_id == user_id.value,
            CollectionItemRow.release_id == release_id.value,
        )
    )
    return collection_item_from_row(row) if row is not None else None


def save_collection_item(session: Session, item: CollectionItem) -> None:
    existing = session.scalar(
        sa.select(CollectionItemRow).where(
            CollectionItemRow.user_id == item.user_id.value,
            CollectionItemRow.release_id == item.release_id.value,
        )
    )
    row = collection_item_to_row(item)
    if existing is not None:
        row.id = existing.id
    session.merge(row)
    session.commit()
