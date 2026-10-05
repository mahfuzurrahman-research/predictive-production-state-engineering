from __future__ import annotations

from math import sqrt


def mae(actual: list[float], forecast: list[float]) -> float:
    if len(actual) != len(forecast) or not actual:
        raise ValueError("non-empty equal-length vectors required")
    return sum(abs(a - f) for a, f in zip(actual, forecast)) / len(actual)


def rmse(actual: list[float], forecast: list[float]) -> float:
    if len(actual) != len(forecast) or not actual:
        raise ValueError("non-empty equal-length vectors required")
    return sqrt(sum((a - f) ** 2 for a, f in zip(actual, forecast)) / len(actual))


def pinball(observed: float, forecast_quantile: float, q: float) -> float:
    if not 0 < q < 1:
        raise ValueError("q must be between 0 and 1")
    u = observed - forecast_quantile
    return max(q * u, (q - 1) * u)
