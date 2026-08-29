"""IngestOutcome: Created | AlreadyExists | AmbiguousMatch | NotFound.

See design doc §3 Closed sum types. Ingestion is modeled as producing one
of these, not as an exception or a boolean. `T` is whatever domain entity
was (or would be) created; `C` is a candidate shown to the user to resolve
an AmbiguousMatch. Both are filled in concretely by the ingestion pipeline
(design doc §4.2, not yet implemented).
"""

from __future__ import annotations

import attrs


@attrs.frozen(slots=True)
class Created[T]:
    value: T


@attrs.frozen(slots=True)
class AlreadyExists[T]:
    value: T


@attrs.frozen(slots=True)
class AmbiguousMatch[C]:
    candidates: tuple[C, ...]


@attrs.frozen(slots=True)
class NotFound:
    pass


type IngestOutcome[T, C] = Created[T] | AlreadyExists[T] | AmbiguousMatch[C] | NotFound
