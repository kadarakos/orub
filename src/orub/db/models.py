"""SQLAlchemy schema for catalog entities. See design doc §4.3, TODO.md Phase 3.

This is a separate representation from `orub.domain.catalog` -- explicit
mapping functions in `mapping.py` convert both ways, so no ORM type ever
leaks into domain/business logic (design doc §4.3).

Scoped to the catalog side only (Release/Track) for this slice. No
`artists`/`labels` tables yet: the domain layer doesn't currently carry
artist/label *names* anywhere reachable from a `Release` (see
`orub.discogs.mapping` -- only ids survive into `Release`/`Track`), so a
table with only an id column would be pure ORM ceremony with nothing to
store. `label_id`/`artist_id` are plain integer columns here, matching what
the domain actually has today; revisit once ingestion captures names.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ReleaseRow(Base):
    __tablename__ = "releases"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    label_id: Mapped[int]
    year: Mapped[int]
    format: Mapped[str]

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
