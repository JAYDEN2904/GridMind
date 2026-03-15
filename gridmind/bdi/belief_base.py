"""
ECGCentralDispatchBeliefs — the belief layer of the BDI architecture.

Maintains the ECG Central Dispatch agent's world model: district demands,
renewable bids, active faults, forecasts, and Contract Net state.  Every
mutation goes through update() to guarantee a full audit trail with
reason chains.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from gridmind.config import DISTRICT_CONFIG


def _init_district_demands() -> dict[str, float]:
    return {name: 0.0 for name in DISTRICT_CONFIG}


def _init_renewable_bids() -> dict[str, float]:
    return {'kaleo_solar': 0.0, 'nzema_solar': 0.0, 'keta_wind': 0.0}


@dataclass
class ECGCentralDispatchBeliefs:
    """Typed belief base for the ECG Central Dispatch BDI agent."""

    district_demands: dict[str, float] = field(default_factory=_init_district_demands)
    total_managed_capacity_mw: float = 1015.0
    renewable_bids: dict[str, float] = field(default_factory=_init_renewable_bids)
    total_renewable_available_mw: float = 0.0
    active_faults: list[str] = field(default_factory=list)
    forecast: dict[str, float] = field(default_factory=dict)
    demand_response_active: bool = False
    pending_cnp_id: str | None = None
    pending_cnp_proposals: list[dict[str, Any]] = field(default_factory=list)
    current_desire: str = 'MONITOR'
    current_intention: str = 'passive_monitoring'
    audit_log: list[dict[str, Any]] = field(default_factory=list)

    def update(self, key: str, value: Any, reason: str, tick: int) -> None:
        """Mutate a single belief field and record the change with a reason chain."""
        old_value = copy.deepcopy(getattr(self, key))
        setattr(self, key, value)
        self.audit_log.append({
            'tick': tick,
            'agent': 'ecg_central_dispatch',
            'belief_updated': key,
            'old': old_value,
            'new': value,
            'reason': reason,
        })

    def get_total_demand(self) -> float:
        """Sum of current demand across all five districts (MW)."""
        return sum(self.district_demands.values())

    def get_utilisation_pct(self) -> float:
        """Current total demand as a fraction of managed capacity."""
        return self.get_total_demand() / self.total_managed_capacity_mw

    def is_demand_rising(self) -> bool:
        """True when more than 2 districts have demand within 10% of their ceiling."""
        count = 0
        for district, demand_mw in self.district_demands.items():
            ceiling = DISTRICT_CONFIG[district]['ceiling_mw']
            if demand_mw >= ceiling * 0.90:
                count += 1
        return count > 2
