"""Result[T, E]: Ok | Err, for expected failures. See design doc §2."""

from __future__ import annotations

from collections.abc import Callable

import attrs


@attrs.frozen(slots=True)
class Ok[T]:
    value: T


@attrs.frozen(slots=True)
class Err[E]:
    error: E


type Result[T, E] = Ok[T] | Err[E]


def is_ok[T, E](result: Result[T, E]) -> bool:
    return isinstance(result, Ok)


def is_err[T, E](result: Result[T, E]) -> bool:
    return isinstance(result, Err)


def map_ok[T, E, U](result: Result[T, E], fn: Callable[[T], U]) -> Result[U, E]:
    match result:
        case Ok(value=value):
            return Ok(fn(value))
        case Err() as err:
            return err


def map_err[T, E, F](result: Result[T, E], fn: Callable[[E], F]) -> Result[T, F]:
    match result:
        case Ok() as ok:
            return ok
        case Err(error=error):
            return Err(fn(error))


def and_then[T, E, U](result: Result[T, E], fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
    match result:
        case Ok(value=value):
            return fn(value)
        case Err() as err:
            return err


def unwrap_or[T, E](result: Result[T, E], default: T) -> T:
    match result:
        case Ok(value=value):
            return value
        case Err():
            return default
