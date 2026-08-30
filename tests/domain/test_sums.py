from orub.domain.sums import Bpm, Condition, EdgeSource, MusicalKey, RecordFormat


def test_edge_source_has_exactly_auto_and_manual() -> None:
    assert {member.value for member in EdgeSource} == {"auto", "manual"}


def test_condition_has_8_discogs_grades() -> None:
    assert len(Condition) == 8
    assert Condition.MINT.value == "Mint (M)"


def test_record_format_members() -> None:
    assert {member.value for member in RecordFormat} == {
        "Vinyl",
        "CD",
        "Cassette",
        "File",
        "Lathe Cut",
    }


def test_musical_key_has_24_camelot_positions() -> None:
    assert len(MusicalKey) == 24
    values = {member.value for member in MusicalKey}
    assert "1A" in values
    assert "12B" in values


def test_bpm_is_frozen_value_type() -> None:
    assert Bpm(120.0) == Bpm(120.0)
    assert Bpm(120.0) != Bpm(128.0)


def test_edge_source_exhaustive_match() -> None:
    def describe(source: EdgeSource) -> str:
        match source:
            case EdgeSource.AUTO:
                return "auto"
            case EdgeSource.MANUAL:
                return "manual"

    assert describe(EdgeSource.AUTO) == "auto"
    assert describe(EdgeSource.MANUAL) == "manual"
