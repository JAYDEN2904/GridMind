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


async def presentation_showcase(
    env: GhanaGridEnvironment,
    dispatch_agent: Any,
    tick_interval: float,
) -> None:
    """Orchestrated 20-tick showcase that exercises all 5 BDI desires.

    Timeline:
        Ticks  1-3:  MONITOR              (natural low demand)
        Ticks  4-7:  OPTIMISE_RENEWABLES  (solar online + util >70%)
        Ticks  8-9:  RESPOND_TO_FAULT     (fault injected)
        Ticks 10-12: PREEMPTIVE_RESPONSE  (fault cleared, forecast >85%)
        Ticks 13-16: EMERGENCY_STABILISE  (demand surge 1.30x)
        Ticks 17-19: MONITOR              (surge cleared, recovery)
    """
    # ── Phase 1: Wait for tick 8, then inject fault ──────────
    while env.tick < 8:
        await asyncio.sleep(tick_interval * 0.5)

    print(
        "\n[PRESENTATION] ═══════════════════════════════════════════"
        "\n[PRESENTATION]  PHASE: RESPOND_TO_FAULT"
        "\n[PRESENTATION]  GRIDCo Volta-Kumasi 161kV line trip"
        "\n[PRESENTATION] ═══════════════════════════════════════════"
    )
    faults = dispatch_agent.beliefs.active_faults.copy()
    if 'kumasi_suame' not in faults:
        faults.append('kumasi_suame')
    dispatch_agent.beliefs.update(
        'active_faults', faults,
        'PRESENTATION: GRIDCo line trip — Kumasi transmission fault',
        env.tick,
    )
    env.district_status['kumasi_suame'] = 'fault'
    env.event_queue.append({'type': 'presentation_fault', 'tick': env.tick})

    # ── Phase 2: Clear fault at tick 10 → fall to PREEMPTIVE ─
    while env.tick < 10:
        await asyncio.sleep(tick_interval * 0.5)

    print(
        "\n[PRESENTATION] ═══════════════════════════════════════════"
        "\n[PRESENTATION]  PHASE: PREEMPTIVE_RESPONSE"
        "\n[PRESENTATION]  Fault cleared — forecast shows Tema >85%"
        "\n[PRESENTATION] ═══════════════════════════════════════════"
    )
    dispatch_agent.beliefs.update(
        'active_faults', [],
        'PRESENTATION: Fault cleared — line restored',
        env.tick,
    )
    env.district_status['kumasi_suame'] = 'normal'

    # ── Phase 3: Demand surge at tick 13 → EMERGENCY ─────────
    while env.tick < 13:
        await asyncio.sleep(tick_interval * 0.5)

    print(
        "\n[PRESENTATION] ═══════════════════════════════════════════"
        "\n[PRESENTATION]  PHASE: EMERGENCY_STABILISE"
        "\n[PRESENTATION]  System-wide demand surge — all districts"
        "\n[PRESENTATION]  near ceiling (1.30x factor applied)"
        "\n[PRESENTATION] ═══════════════════════════════════════════"
    )
    env.scenario_demand_factor = 1.30
    env.event_queue.append({'type': 'presentation_emergency', 'tick': env.tick})

    # ── Phase 4: Clear surge at tick 17 → recovery to MONITOR ─
    while env.tick < 17:
        await asyncio.sleep(tick_interval * 0.5)

    print(
        "\n[PRESENTATION] ═══════════════════════════════════════════"
        "\n[PRESENTATION]  PHASE: RECOVERY → MONITOR"
        "\n[PRESENTATION]  Demand surge subsiding — system stabilising"
        "\n[PRESENTATION] ═══════════════════════════════════════════"
    )
    env.scenario_demand_factor = 1.0
    dispatch_agent.beliefs.update(
        'forecast', {},
        'PRESENTATION: Forecast cleared after emergency recovery',
        env.tick,
    )
    dispatch_agent.beliefs.update(
        'demand_response_active', False,
        'PRESENTATION: DR deactivated — system recovered',
        env.tick,
    )
    for district in env.district_status:
        env.district_status[district] = 'normal'


SCENARIO_MAP: dict[str, ScenarioFn] = {
    'tema_spike': tema_shift_change_spike,
    'akosombo': akosombo_curtailment,
    'spintex': spintex_feeder_fault,
    'line_trip': gridco_line_trip,
    'all_offline': all_renewables_offline,
}
