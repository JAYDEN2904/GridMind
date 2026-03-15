"""
Tests for the ECG Forecast Unit weighted moving average logic.

Exercises the WMA weights and forecast computation from
forecast_unit_agent.py in isolation — no SPADE, no async.
"""
from __future__ import annotations

import pytest

from gridmind.agents.forecast_unit_agent import WEIGHTS
from gridmind.config import (
    DISTRICT_CAPACITY,
    FORECAST_HISTORY_LEN,
    PREEMPTIVE_THRESHOLD_PCT,
)


def _compute_wma(history: list[float], weights: list[float]) -> float:
    """Reproduce the WMA forecast computation from the agent."""
    w = weights[-len(history):]
    w_sum = sum(w)
    w_norm = [x / w_sum for x in w]
    return sum(wi * ri for wi, ri in zip(w_norm, history))


def test_wma_weights_sum_to_one():
    """The 20 WMA weights must sum to 1.0."""
    assert sum(WEIGHTS) == pytest.approx(1.0, abs=1e-6), (
        f"Expected weights to sum to 1.0, got {sum(WEIGHTS)}"
    )
    assert len(WEIGHTS) == FORECAST_HISTORY_LEN, (
        f"Expected {FORECAST_HISTORY_LEN} weights, got {len(WEIGHTS)}"
    )


def test_wma_recent_weighted_higher():
    """The most recent weight must exceed the oldest weight."""
    assert WEIGHTS[-1] > WEIGHTS[0], (
        f"Expected WEIGHTS[-1]={WEIGHTS[-1]} > WEIGHTS[0]={WEIGHTS[0]}"
    )


def test_forecast_rising_trend():
    """A rising history should produce a WMA above the simple mean."""
    history = [100.0, 105.0, 110.0, 115.0, 120.0, 125.0, 130.0]
    simple_mean = sum(history) / len(history)
    forecast = _compute_wma(history, WEIGHTS)

    assert forecast > simple_mean, (
        f"Expected rising-trend WMA {forecast:.1f} > simple mean "
        f"{simple_mean:.1f} due to recency weighting"
    )


def test_forecast_triggers_warning_above_threshold():
    """A forecast exceeding PREEMPTIVE_THRESHOLD_PCT * ceiling must warn."""
    tema_ceiling = DISTRICT_CAPACITY['tema_industrial']
    threshold = tema_ceiling * PREEMPTIVE_THRESHOLD_PCT

    history = [350.0, 355.0, 360.0, 365.0, 370.0, 375.0, 380.0]
    forecast = _compute_wma(history, WEIGHTS)

    assert forecast > threshold, (
        f"Expected forecast {forecast:.1f} MW > threshold {threshold:.1f} MW "
        f"({PREEMPTIVE_THRESHOLD_PCT:.0%} of {tema_ceiling} MW)"
    )


def test_short_history_uses_available_readings():
    """WMA should still compute with fewer readings than the full window."""
    history = [290.0, 295.0]
    forecast = _compute_wma(history, WEIGHTS)

    assert forecast == pytest.approx(293.158, rel=1e-2), (
        f"Expected WMA of [290, 295] ≈ 293.2 with recent weighting, "
        f"got {forecast:.3f}"
    )
    assert 290.0 < forecast < 295.0, (
        f"Forecast {forecast:.1f} should be between 290 and 295"
    )
