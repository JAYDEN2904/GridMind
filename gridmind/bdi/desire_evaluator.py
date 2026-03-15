"""
Desire evaluator — the desire layer of the BDI architecture.

Evaluates ECG Central Dispatch's desires in strict priority order.
The first condition that returns True determines the active desire.
This is a pure function of the belief base — no side effects.
"""
from __future__ import annotations

from typing import Callable

from gridmind.bdi.belief_base import ECGCentralDispatchBeliefs
from gridmind.config import (
    DISTRICT_CONFIG,
    EMERGENCY_THRESHOLD_PCT,
    PREEMPTIVE_THRESHOLD_PCT,
)


def _emergency_stabilise(beliefs: ECGCentralDispatchBeliefs) -> bool:
    return beliefs.get_utilisation_pct() > EMERGENCY_THRESHOLD_PCT


def _respond_to_fault(beliefs: ECGCentralDispatchBeliefs) -> bool:
    return len(beliefs.active_faults) > 0


def _preemptive_response(beliefs: ECGCentralDispatchBeliefs) -> bool:
    for district, forecast_mw in beliefs.forecast.items():
        ceiling = DISTRICT_CONFIG.get(district, {}).get('ceiling_mw', 0.0)
        if forecast_mw > ceiling * PREEMPTIVE_THRESHOLD_PCT:
            return True
    return False


def _optimise_renewables(beliefs: ECGCentralDispatchBeliefs) -> bool:
    return beliefs.total_renewable_available_mw > 0 and beliefs.is_demand_rising()


def _monitor(_beliefs: ECGCentralDispatchBeliefs) -> bool:
    return True


DESIRES: list[tuple[str, Callable[[ECGCentralDispatchBeliefs], bool]]] = [
    ('EMERGENCY_STABILISE', _emergency_stabilise),
    ('RESPOND_TO_FAULT', _respond_to_fault),
    ('PREEMPTIVE_RESPONSE', _preemptive_response),
    ('OPTIMISE_RENEWABLES', _optimise_renewables),
    ('MONITOR', _monitor),
]


def evaluate_desires(beliefs: ECGCentralDispatchBeliefs) -> str:
    """Return the name of the highest-priority desire whose condition holds."""
    for desire_name, condition_fn in DESIRES:
        if condition_fn(beliefs):
            return desire_name
    return 'MONITOR'
