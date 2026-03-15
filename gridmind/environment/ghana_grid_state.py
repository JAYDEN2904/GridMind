"""
GhanaGridEnvironment — shared world state for the GridMind simulation.

Mirrors the physical state of Ghana's national grid across the five
modelled ECG distribution districts and three renewable injection points.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from gridmind.config import (
    DISTRICT_CONFIG,
    RENEWABLE_CONFIG,
    TOTAL_MANAGED_CAPACITY_MW,
)


def _init_district_demand() -> dict[str, float]:
    return {name: cfg['base_demand_mw'] for name, cfg in DISTRICT_CONFIG.items()}


def _init_district_capacity() -> dict[str, float]:
    return {name: cfg['ceiling_mw'] for name, cfg in DISTRICT_CONFIG.items()}


def _init_district_status() -> dict[str, str]:
    return {name: 'normal' for name in DISTRICT_CONFIG}


def _init_renewable_available() -> dict[str, float]:
    return {name: 0.0 for name in RENEWABLE_CONFIG}


def _init_renewable_injecting() -> dict[str, bool]:
    return {name: False for name in RENEWABLE_CONFIG}


@dataclass
class GhanaGridEnvironment:
    """Mutable snapshot of the Ghana national grid at a given simulation tick."""

    district_demand_mw: dict[str, float] = field(default_factory=_init_district_demand)
    district_capacity_mw: dict[str, float] = field(default_factory=_init_district_capacity)
    district_status: dict[str, str] = field(default_factory=_init_district_status)
    renewable_available_mw: dict[str, float] = field(default_factory=_init_renewable_available)
    renewable_injecting: dict[str, bool] = field(default_factory=_init_renewable_injecting)
    tick: int = 0
    event_queue: list[dict[str, Any]] = field(default_factory=list)
    audit_log: list[dict[str, Any]] = field(default_factory=list)

    def tick_forward(self) -> None:
        """Advance the simulation clock by one tick."""
        self.tick += 1

    def log_event(self, agent: str, event_type: str, detail: str) -> None:
        """Append a timestamped event record to the audit log."""
        self.audit_log.append({
            'tick': self.tick,
            'wall_clock': time.time(),
            'agent': agent,
            'event_type': event_type,
            'detail': detail,
        })

    def get_total_demand(self) -> float:
        """Sum of current demand across all five districts (MW)."""
        return sum(self.district_demand_mw.values())

    def get_utilisation_pct(self) -> float:
        """Current total demand as a fraction of managed capacity."""
        return self.get_total_demand() / TOTAL_MANAGED_CAPACITY_MW
