"""SQLAlchemy schema for catalog and tag entities. See design doc §4.3, TODO.md Phase 3.

This is a separate representation from `orub.domain.catalog`/`orub.domain.user`
-- explicit mapping functions in `mapping.py` convert both ways, so no ORM
type ever leaks into domain/business logic (design doc §4.3).

Catalog (Release/Track): no `artists`/`labels` tables yet, since the domain
layer doesn't currently carry artist/label *names* anywhere reachable from a
`Release` (see `orub.discogs.mapping` -- only ids survive into
`Release`/`Track`), so a table with only an id column would be pure ORM
ceremony with nothing to store. `label_id`/`artist_id` are plain integer
columns here, matching what the domain actually has today; revisit once
ingestion captures names.

Tags (TagCategory/Tag): user-owned vocabulary. `Edge` and real `user_id`
scoping are still deferred (there's no auth yet -- see
`orub.domain.user.DEFAULT_USER_ID`).

CollectionItem: "this user owns this release". Has its own surrogate `id`
for join-table convenience, but is identified in the domain by the
`(user_id, release_id)` pair (see `orub.db.collection`), not by that id.
"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ReleaseRow(Base):
    __tablename__ = "releases"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    label_id: Mapped[int]
    year: Mapped[int | None]
    format: Mapped[str]
    catno: Mapped[str | None]

    tracks: Mapped[list[TrackRow]] = relationship(
        back_populates="release", cascade="all, delete-orphan", order_by="TrackRow.position"
    )


class TrackRow(Base):
    __tablename__ = "tracks"

    release_id: Mapped[int] = mapped_column(sa.ForeignKey("releases.id"), primary_key=True)
    position: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    bpm: Mapped[float | None]
    key: Mapped[str | None]

    release: Mapped[ReleaseRow] = relationship(back_populates="tracks")
    artist_ids: Mapped[list[TrackArtistRow]] = relationship(
        cascade="all, delete-orphan", order_by="TrackArtistRow.artist_id"
    )


class TrackArtistRow(Base):
    __tablename__ = "track_artist_ids"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["release_id", "track_position"], ["tracks.release_id", "tracks.position"]
        ),
    )

    release_id: Mapped[int] = mapped_column(primary_key=True)
    track_position: Mapped[str] = mapped_column(primary_key=True)
    artist_id: Mapped[int] = mapped_column(primary_key=True)


class TagCategoryRow(Base):
    __tablename__ = "tag_categories"
    __table_args__ = (sa.UniqueConstraint("user_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    name: Mapped[str]

    tags: Mapped[list[TagRow]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class TagRow(Base):
    __tablename__ = "tags"
    __table_args__ = (sa.UniqueConstraint("category_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    category_id: Mapped[int] = mapped_column(sa.ForeignKey("tag_categories.id"))
    name: Mapped[str]

    category: Mapped[TagCategoryRow] = relationship(back_populates="tags")


class CollectionItemRow(Base):
    __tablename__ = "collection_items"
    __table_args__ = (sa.UniqueConstraint("user_id", "release_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    release_id: Mapped[int] = mapped_column(sa.ForeignKey("releases.id"))
    condition: Mapped[str]
    notes: Mapped[str]
    date_added: Mapped[datetime]

    tags: Mapped[list[CollectionItemTagRow]] = relationship(
        cascade="all, delete-orphan", order_by="CollectionItemTagRow.tag_id"
    )


class CollectionItemTagRow(Base):
    __tablename__ = "collection_item_tags"

    collection_item_id: Mapped[int] = mapped_column(
        sa.ForeignKey("collection_items.id"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(sa.ForeignKey("tags.id"), primary_key=True)
