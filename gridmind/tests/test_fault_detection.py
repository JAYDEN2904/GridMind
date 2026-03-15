"""
Tests for the GRIDCo fault detection statistical logic.

Reproduces the anomaly-detection rules from fault_watch_agent.py
(spike detection and feeder-loss detection) using numpy in isolation
— no SPADE agent instantiation.
"""
from __future__ import annotations

import numpy as np

from gridmind.config import FAULT_SIGMA_THRESHOLD


def _detect(window: list[float], new_reading: float) -> dict[str, bool]:
    """Reproduce the fault_watch_agent detection rules.

    Returns dict with 'spike' and 'feeder_loss' boolean flags.
    """
    full_window = window + [new_reading]

    if len(full_window) < 3:
        return {'spike': False, 'feeder_loss': False}

    mean = float(np.mean(full_window))
    std = float(np.std(full_window))

    spike = (
        std >= 0.1
        and new_reading > mean + FAULT_SIGMA_THRESHOLD * std
    )

    feeder_loss = new_reading < mean * 0.15 and mean > 50

    return {'spike': spike, 'feeder_loss': feeder_loss}


def test_spike_detected_above_2sigma():
    """A reading far above the window mean should trigger a spike."""
    window = [290.0, 292.0, 288.0, 291.0, 290.0]
    result = _detect(window, 380.0)

    assert result['spike'] is True, (
        "Expected spike detection for reading 380 MW "
        "against window ~290 MW"
    )


def test_normal_reading_not_flagged():
    """A reading within normal range should not trigger a spike."""
    window = [290.0, 292.0, 288.0, 291.0, 290.0]
    result = _detect(window, 293.0)

    assert result['spike'] is False, (
        "Expected no spike for reading 293 MW within normal range"
    )
    assert result['feeder_loss'] is False, (
        "Expected no feeder_loss for reading 293 MW"
    )


def test_feeder_loss_detected():
    """A near-zero reading against a high mean should trigger feeder_loss."""
    window = [140.0, 142.0, 139.0, 141.0, 140.0]
    result = _detect(window, 3.5)

    assert result['feeder_loss'] is True, (
        "Expected feeder_loss for reading 3.5 MW "
        "against window ~140 MW"
    )


def test_insufficient_window_skips_detection():
    """With fewer than 3 readings total, no detection should occur."""
    window = [290.0]
    result = _detect(window, 380.0)

    assert result['spike'] is False, (
        "Expected no spike with insufficient window (2 readings)"
    )
    assert result['feeder_loss'] is False, (
        "Expected no feeder_loss with insufficient window"
    )


def test_stdev_near_zero_skips_spike_check():
    """A flat window (std~0) must not produce a false spike."""
    window = [290.0, 290.0, 290.0, 290.0, 290.0]
    result = _detect(window, 290.0)

    assert result['spike'] is False, (
        "Expected no spike when std is near zero (flat window)"
    )
