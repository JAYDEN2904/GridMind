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
    DAY_CYCLE_TICKS,
    DISTRICT_CONFIG,
    RENEWABLE_CONFIG,
    TOTAL_MANAGED_CAPACITY_MW,
)

_DEMAND_PROFILES: dict[str, list[float]] = {
    # tema_industrial (base 290 MW, ceiling 400 MW)
    # Twin shift-change spikes at ticks 4 and 14; moderate overnight
    'tema_industrial': [
        0.82, 0.80, 0.82,        # ticks 0-2:   night
        1.05, 1.25,               # ticks 3-4:   dawn + shift spike #1
        1.10, 1.15, 1.18,         # ticks 5-7:   sustained morning ramp
        1.22, 1.20, 1.15,         # ticks 8-10:  industrial plateau
        1.00, 1.05,               # ticks 11-12: afternoon build
        1.20, 1.30,               # ticks 13-14: shift spike #2
        1.15, 1.05, 0.95,         # ticks 15-17: evening decline
        0.88, 0.82,               # ticks 18-19: late night
    ],
    # accra_central (base 140 MW, ceiling 190 MW)
    # Business-hours ramp peaking at midday; sharp evening dip
    'accra_central': [
        0.65, 0.62, 0.65,        # ticks 0-2:   night
        0.72, 0.80,               # ticks 3-4:   dawn
        0.92, 1.02, 1.10,         # ticks 5-7:   morning ramp
        1.15, 1.18, 1.15,         # ticks 8-10:  midday peak (165 MW)
        1.10, 1.05,               # ticks 11-12: afternoon
        0.95, 0.85,               # ticks 13-14: evening transition
        0.75, 0.70, 0.68,         # ticks 15-17: evening dip
        0.65, 0.63,               # ticks 18-19: late night
    ],
    # kumasi_suame (base 110 MW, ceiling 150 MW)
    # Gradual morning ramp, flat midday, soft evening peak
    'kumasi_suame': [
        0.75, 0.72, 0.75,        # ticks 0-2:   night
        0.80, 0.85,               # ticks 3-4:   dawn
        0.92, 1.00, 1.05,         # ticks 5-7:   morning ramp
        1.08, 1.10, 1.08,         # ticks 8-10:  midday
        1.05, 1.02,               # ticks 11-12: afternoon
        1.00, 1.05,               # ticks 13-14: pre-evening
        1.12, 1.10, 1.05,         # ticks 15-17: soft evening peak
        0.85, 0.78,               # ticks 18-19: late night
    ],
    # kasoa_corridor (base 65 MW, ceiling 100 MW)
    # Low daytime; strong residential evening peak near ceiling
    'kasoa_corridor': [
        0.70, 0.65, 0.68,        # ticks 0-2:   night
        0.70, 0.72,               # ticks 3-4:   dawn
        0.75, 0.78, 0.80,         # ticks 5-7:   daytime
        0.82, 0.80, 0.82,         # ticks 8-10:  midday
        0.85, 0.90,               # ticks 11-12: afternoon
        1.00, 1.15,               # ticks 13-14: pre-evening rise
        1.45, 1.48, 1.35,         # ticks 15-17: evening surge (96 MW)
        1.05, 0.85,               # ticks 18-19: late night
    ],
    # takoradi_harbour (base 125 MW, ceiling 175 MW)
    # Flat port operations with slight night-shift bump
    'takoradi_harbour': [
        1.08, 1.10, 1.08,        # ticks 0-2:   night shift (+20 MW)
        1.02, 0.98,               # ticks 3-4:   dawn
        0.95, 0.95, 0.98,         # ticks 5-7:   daytime
        1.00, 1.00, 1.02,         # ticks 8-10:  midday
        1.02, 1.00,               # ticks 11-12: afternoon
        0.98, 1.00,               # ticks 13-14: pre-evening
        1.05, 1.08, 1.10,         # ticks 15-17: evening
        1.12, 1.10,               # ticks 18-19: night shift returns
    ],
}


def _demand_multiplier(district_id: str, tick: int) -> float:
    """Return the demand multiplier for a district at the given tick."""
    profile = _DEMAND_PROFILES[district_id]
    return profile[tick % DAY_CYCLE_TICKS]


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
    scenario_demand_factor: float = 1.0
    event_queue: list[dict[str, Any]] = field(default_factory=list)
    audit_log: list[dict[str, Any]] = field(default_factory=list)

    def tick_forward(self) -> None:
        """Advance the simulation clock and update district demand profiles."""
        self.tick += 1
        for district, cfg in DISTRICT_CONFIG.items():
            base = cfg['base_demand_mw']
            multiplier = _demand_multiplier(district, self.tick)
            self.district_demand_mw[district] = (
                base * multiplier * self.scenario_demand_factor
            )

            if self.district_status[district] in ('fault', 'shedding'):
                continue
            ceiling = cfg['ceiling_mw']
            util = self.district_demand_mw[district] / ceiling if ceiling else 0
            self.district_status[district] = 'warning' if util >= 0.95 else 'normal'

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
