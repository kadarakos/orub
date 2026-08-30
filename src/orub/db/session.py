"""Engine setup. See design doc §4.3, §7.

SQLite locally for now (`Settings.database_url`); Neon Postgres is the
Phase 8 deploy target, swapped in via the same engine URL. No Alembic yet
(TODO.md Phase 3) -- the schema isn't stable enough to be worth migrating,
so `create_all` is the whole story until it settles.
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

from orub.db.models import Base


def make_engine(database_url: str) -> Engine:
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine
