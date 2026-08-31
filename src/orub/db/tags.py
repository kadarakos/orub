"""Tag/TagCategory repository functions. See design doc §4.3, TODO.md Phase 3.

User-owned (unlike `orub.db.repository`, which is catalog-only), but scoped
by a hardcoded `user_id` argument rather than a real auth dependency -- see
`orub.domain.user.DEFAULT_USER_ID`. Get-or-create is intentionally not
race-safe (no `SELECT ... FOR UPDATE`/upsert): this is a single-user local
SQLite tool, not a concurrent multi-writer system.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Session

from orub.db.mapping import tag_category_from_row, tag_from_row
from orub.db.models import TagCategoryRow, TagRow
from orub.discogs.mapping import DiscogsTagHints
from orub.domain.identity import TagCategoryId, TagId
from orub.domain.user import Tag, TagCategory, UserId


def list_tag_categories(session: Session, user_id: UserId) -> tuple[TagCategory, ...]:
    rows = session.scalars(
        sa.select(TagCategoryRow)
        .where(TagCategoryRow.user_id == user_id.value)
        .order_by(TagCategoryRow.name)
    )
    return tuple(tag_category_from_row(row) for row in rows)


def list_tags(session: Session, user_id: UserId, category_id: TagCategoryId) -> tuple[Tag, ...]:
    rows = session.scalars(
        sa.select(TagRow)
        .where(TagRow.user_id == user_id.value, TagRow.category_id == category_id.value)
        .order_by(TagRow.name)
    )
    return tuple(tag_from_row(row) for row in rows)


def get_or_create_tag_category(session: Session, user_id: UserId, name: str) -> TagCategory:
    row = session.scalar(
        sa.select(TagCategoryRow).where(
            TagCategoryRow.user_id == user_id.value, TagCategoryRow.name == name
        )
    )
    if row is None:
        row = TagCategoryRow(user_id=user_id.value, name=name)
        session.add(row)
        session.flush()
    return tag_category_from_row(row)


def get_or_create_tag(
    session: Session, user_id: UserId, category_id: TagCategoryId, name: str
) -> Tag:
    row = session.scalar(
        sa.select(TagRow).where(TagRow.category_id == category_id.value, TagRow.name == name)
    )
    if row is None:
        row = TagRow(user_id=user_id.value, category_id=category_id.value, name=name)
        session.add(row)
        session.flush()
    return tag_from_row(row)


_DISCOGS_TAG_CATEGORIES = ("genre", "style", "format")


def apply_discogs_tag_hints(
    session: Session, user_id: UserId, hints: DiscogsTagHints
) -> tuple[TagId, ...]:
    """Get-or-create a `Tag` under a reserved category for every value in
    `hints`, growing the user's tag vocabulary from what Discogs reports.
    """
    values_by_category = dict(
        zip(_DISCOGS_TAG_CATEGORIES, (hints.genres, hints.styles, hints.format_descriptions))
    )
    tag_ids: list[TagId] = []
    for category_name in _DISCOGS_TAG_CATEGORIES:
        values = values_by_category[category_name]
        if not values:
            continue
        category = get_or_create_tag_category(session, user_id, category_name)
        for value in values:
            tag = get_or_create_tag(session, user_id, category.id, value)
            tag_ids.append(tag.id)
    session.commit()
    return tuple(tag_ids)
