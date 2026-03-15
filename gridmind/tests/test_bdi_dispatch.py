"""
Tests for the BDI logic modules: desire evaluator, belief base, and
intention selector.  Pure unit tests — no SPADE, no async.
"""
from __future__ import annotations

from gridmind.bdi.belief_base import ECGCentralDispatchBeliefs
from gridmind.bdi.desire_evaluator import DESIRES, evaluate_desires
from gridmind.bdi.intention_selector import select_intention
from gridmind.config import DISTRICT_CONFIG


def test_monitor_desire_when_normal(fresh_beliefs: ECGCentralDispatchBeliefs):
    """At base demand (all zeros), the desire should be MONITOR."""
    result = evaluate_desires(fresh_beliefs)
    assert result == 'MONITOR', (
        f"Expected MONITOR at zero demand, got {result}"
    )


def test_emergency_desire_at_98pct(fresh_beliefs: ECGCentralDispatchBeliefs):
    """When all districts are at 99% of ceiling, desire is EMERGENCY_STABILISE."""
    for district, cfg in DISTRICT_CONFIG.items():
        fresh_beliefs.district_demands[district] = cfg['ceiling_mw'] * 0.99

    result = evaluate_desires(fresh_beliefs)
    assert result == 'EMERGENCY_STABILISE', (
        f"Expected EMERGENCY_STABILISE at 99% utilisation, got {result}"
    )


def test_fault_desire_overrides_monitor(fresh_beliefs: ECGCentralDispatchBeliefs):
    """Active faults should trigger RESPOND_TO_FAULT over MONITOR."""
    fresh_beliefs.active_faults = ['tema_industrial']

    result = evaluate_desires(fresh_beliefs)
    assert result == 'RESPOND_TO_FAULT', (
        f"Expected RESPOND_TO_FAULT with active fault, got {result}"
    )


def test_preemptive_desire_from_forecast(fresh_beliefs: ECGCentralDispatchBeliefs):
    """A high forecast should trigger PREEMPTIVE_RESPONSE."""
    fresh_beliefs.forecast = {'tema_industrial': 395.0}

    result = evaluate_desires(fresh_beliefs)
    assert result == 'PREEMPTIVE_RESPONSE', (
        f"Expected PREEMPTIVE_RESPONSE with forecast 395 MW "
        f"(threshold 340 MW), got {result}"
    )


def test_desire_priority_emergency_over_fault(
    fresh_beliefs: ECGCentralDispatchBeliefs,
):
    """EMERGENCY_STABILISE must outrank RESPOND_TO_FAULT."""
    for district, cfg in DISTRICT_CONFIG.items():
        fresh_beliefs.district_demands[district] = cfg['ceiling_mw'] * 0.99
    fresh_beliefs.active_faults = ['tema_industrial']

    result = evaluate_desires(fresh_beliefs)
    assert result == 'EMERGENCY_STABILISE', (
        f"Expected EMERGENCY_STABILISE to beat RESPOND_TO_FAULT, got {result}"
    )


def test_belief_update_appends_audit(fresh_beliefs: ECGCentralDispatchBeliefs):
    """beliefs.update() must append exactly one audit log entry."""
    fresh_beliefs.update('demand_response_active', True, 'test reason', 1)

    assert len(fresh_beliefs.audit_log) == 1, (
        f"Expected 1 audit entry, got {len(fresh_beliefs.audit_log)}"
    )
    entry = fresh_beliefs.audit_log[0]
    assert entry['belief_updated'] == 'demand_response_active', (
        f"Expected belief_updated='demand_response_active', "
        f"got '{entry['belief_updated']}'"
    )
    assert entry['new'] is True, "Expected new value to be True"
    assert entry['old'] is False, "Expected old value to be False"
    assert entry['tick'] == 1, f"Expected tick=1, got {entry['tick']}"


def test_intention_mapping_complete():
    """Every desire in DESIRES must map to a non-None intention string."""
    for desire_name, _ in DESIRES:
        intention = select_intention(desire_name)
        assert intention is not None, (
            f"select_intention returned None for desire '{desire_name}'"
        )
        assert isinstance(intention, str) and len(intention) > 0, (
            f"Intention for '{desire_name}' must be a non-empty string, "
            f"got {intention!r}"
        )
