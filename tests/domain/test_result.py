from orub.domain.result import Err, Ok, and_then, is_err, is_ok, map_err, map_ok, unwrap_or


def _increment(x: int) -> int:
    return x + 1


def test_ok_is_ok_not_err() -> None:
    result = Ok(5)
    assert is_ok(result)
    assert not is_err(result)


def test_err_is_err_not_ok() -> None:
    result = Err("boom")
    assert is_err(result)
    assert not is_ok(result)


def test_map_ok_transforms_ok_value() -> None:
    assert map_ok(Ok(5), _increment) == Ok(6)


def test_map_ok_passes_through_err() -> None:
    assert map_ok(Err("boom"), _increment) == Err("boom")


def test_map_err_transforms_err_value() -> None:
    assert map_err(Err("boom"), str.upper) == Err("BOOM")


def test_map_err_passes_through_ok() -> None:
    assert map_err(Ok(5), str.upper) == Ok(5)


def test_and_then_chains_ok() -> None:
    def half(x: int) -> Ok[int] | Err[str]:
        return Ok(x // 2) if x % 2 == 0 else Err("odd")

    assert and_then(Ok(4), half) == Ok(2)
    assert and_then(Ok(3), half) == Err("odd")


def test_and_then_short_circuits_err() -> None:
    def half(x: int) -> Ok[int] | Err[str]:
        return Ok(x // 2)

    assert and_then(Err("already broken"), half) == Err("already broken")


def test_unwrap_or_returns_ok_value() -> None:
    assert unwrap_or(Ok(5), 0) == 5


def test_unwrap_or_returns_default_on_err() -> None:
    assert unwrap_or(Err("boom"), 0) == 0


def test_ok_and_err_are_frozen() -> None:
    ok = Ok(5)
    try:
        ok.value = 6  # type: ignore[misc]
    except (AttributeError, TypeError):
        pass
    else:
        raise AssertionError("Ok should be immutable")


def test_ok_equality_is_by_value() -> None:
    assert Ok(5) == Ok(5)
    assert Ok(5) != Ok(6)
    assert Err("a") == Err("a")
    assert Err("a") != Err("b")
