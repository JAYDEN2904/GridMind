"""
Named event scenarios for the GridMind Ghana grid simulation.

Each scenario is an async function that mutates the shared
GhanaGridEnvironment to inject a realistic grid disturbance.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from gridmind.config import DISTRICT_BASE_DEMAND, TICK_INTERVAL
from gridmind.environment.ghana_grid_state import GhanaGridEnvironment

ScenarioFn = Callable[[GhanaGridEnvironment], Coroutine[Any, Any, None]]


async def akosombo_curtailment(env: GhanaGridEnvironment) -> None:
    """Akosombo Dam low-water season — gradual supply erosion."""
    print(
        "[EVENT] 🌊 AKOSOMBO CURTAILMENT: Reservoir at critical "
        "low — VRA reducing output by 40%"
    )
    for district in ['tema_industrial', 'accra_central']:
        env.district_demand_mw[district] *= 1.12
    env.event_queue.append({'type': 'akosombo_curtailment', 'tick': env.tick})


async def tema_shift_change_spike(env: GhanaGridEnvironment) -> None:
    """Tema Heavy Industrial 06:00/18:00 simultaneous shift-change."""
    print(
        "[EVENT] 🏭 TEMA SHIFT SPIKE: 6am/6pm industrial "
        "shift-change — demand surge"
    )
    env.district_demand_mw['tema_industrial'] *= 1.22
    env.district_demand_mw['takoradi_harbour'] *= 1.08
    env.event_queue.append({'type': 'tema_shift_spike', 'tick': env.tick})


async def spintex_feeder_fault(env: GhanaGridEnvironment) -> None:
    """ECG feeder cable fault on the Spintex Road corridor."""
    print(
        "[EVENT] ⚠ SPINTEX ROAD FAULT: ECG feeder cable fault "
        "— Accra Central sensor loss"
    )
    env.district_demand_mw['accra_central'] = 2.0
    env.district_status['accra_central'] = 'fault'
    env.event_queue.append({'type': 'spintex_feeder_fault', 'tick': env.tick})

    await asyncio.sleep(8 * TICK_INTERVAL)

    env.district_demand_mw['accra_central'] = DISTRICT_BASE_DEMAND['accra_central']
    env.district_status['accra_central'] = 'normal'
    print("[EVENT] ✅ SPINTEX ROAD: Feeder restored")


async def gridco_line_trip(env: GhanaGridEnvironment) -> None:
    """GRIDCo Volta-Kumasi 161kV inter-regional line trip."""
    print(
        "[EVENT] 🔗 GRIDCO LINE TRIP: Volta-Kumasi 161kV "
        "transmission fault — Kumasi capacity reduced"
    )
    env.district_capacity_mw['kumasi_suame'] *= 0.40
    env.district_demand_mw['kumasi_suame'] = min(
        env.district_demand_mw['kumasi_suame'],
        env.district_capacity_mw['kumasi_suame'] * 0.95,
    )
    env.event_queue.append({'type': 'gridco_line_trip', 'tick': env.tick})


async def all_renewables_offline(env: GhanaGridEnvironment) -> None:
    """Simulate combined cloud cover + calm wind — all renewables drop."""
    print(
        "[EVENT] ☁ ALL RENEWABLES OFFLINE: Cloud cover + "
        "wind calm — Kaleo/Nzema/Keta near zero"
    )
    for source in ['kaleo_solar', 'nzema_solar', 'keta_wind']:
        env.renewable_available_mw[source] = 0.5
    env.event_queue.append({'type': 'all_renewables_offline', 'tick': env.tick})


SCENARIO_MAP: dict[str, ScenarioFn] = {
    'tema_spike': tema_shift_change_spike,
    'akosombo': akosombo_curtailment,
    'spintex': spintex_feeder_fault,
    'line_trip': gridco_line_trip,
    'all_offline': all_renewables_offline,
}
