"""
Intention selector — the intention layer of the BDI architecture.

Maps each desire to a concrete plan name (intention) and provides
helpers for detecting desire transitions that trigger intention
reconsideration.
"""
from __future__ import annotations

DESIRE_TO_INTENTION: dict[str, str] = {
    'EMERGENCY_STABILISE': 'initiate_contract_net',
    'RESPOND_TO_FAULT': 'emergency_contract_net',
    'PREEMPTIVE_RESPONSE': 'initiate_contract_net',
    'OPTIMISE_RENEWABLES': 'optimise_renewable_mix',
    'MONITOR': 'passive_monitoring',
}


def select_intention(desire: str) -> str:
    """Return the intention (plan name) that realises the given desire."""
    return DESIRE_TO_INTENTION[desire]


def has_desire_changed(old_desire: str, new_desire: str) -> bool:
    """True when the agent's active desire has shifted, requiring reconsideration."""
    return old_desire != new_desire
