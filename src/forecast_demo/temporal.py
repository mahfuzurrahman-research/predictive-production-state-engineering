from __future__ import annotations

from dataclasses import dataclass
from datetime import date


class TemporalError(ValueError):
    pass


@dataclass(frozen=True)
class VintageValue:
    available_date: date
    value: float


def admit_as_of(value: VintageValue, origin_date: date) -> float:
    """Return a value only when it was available by the forecast origin."""
    if value.available_date > origin_date:
        raise TemporalError("future information is not admissible")
    return value.value


def validate_pair(origin_date: date, target_date: date) -> None:
    if target_date <= origin_date:
        raise TemporalError("target must occur after origin")
