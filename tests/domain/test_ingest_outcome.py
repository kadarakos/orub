from orub.domain.ingest_outcome import (
    AlreadyExists,
    AmbiguousMatch,
    Created,
    IngestOutcome,
    NotFound,
)


def test_created_carries_value() -> None:
    outcome: IngestOutcome[int, str] = Created(1)
    assert outcome == Created(1)


def test_already_exists_carries_value() -> None:
    outcome: IngestOutcome[int, str] = AlreadyExists(1)
    assert outcome == AlreadyExists(1)


def test_ambiguous_match_carries_candidates() -> None:
    outcome: IngestOutcome[int, str] = AmbiguousMatch(("a", "b"))
    assert outcome == AmbiguousMatch(("a", "b"))


def test_not_found_is_a_singleton_value() -> None:
    outcome: IngestOutcome[int, str] = NotFound()
    assert outcome == NotFound()


def test_ingest_outcome_exhaustive_match() -> None:
    def describe(outcome: IngestOutcome[int, str]) -> str:
        match outcome:
            case Created(value=value):
                return f"created {value}"
            case AlreadyExists(value=value):
                return f"already exists {value}"
            case AmbiguousMatch(candidates=candidates):
                return f"ambiguous {candidates}"
            case NotFound():
                return "not found"

    assert describe(Created(1)) == "created 1"
    assert describe(AlreadyExists(1)) == "already exists 1"
    assert describe(AmbiguousMatch(("a", "b"))) == "ambiguous ('a', 'b')"
    assert describe(NotFound()) == "not found"
