"""
GridMind — main simulation entry point.

Boots all 12 SPADE agents, injects an optional scenario, runs the
simulation loop with the Rich terminal dashboard and metrics collector,
and prints a final KPI report on completion.

Usage:
    python -m gridmind.main
    python -m gridmind.main --demo-mode
    python -m gridmind.main --scenario tema_spike
    python -m gridmind.main --scenario full_stress --demo-mode
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from gridmind.agents.demand_response_agent import AccraIndustrialDRAgent
from gridmind.agents.ecg_central_dispatch import ECGCentralDispatchAgent
from gridmind.agents.fault_watch_agent import GRIDCoFaultWatchAgent
from gridmind.agents.forecast_unit_agent import ECGForecastUnitAgent
from gridmind.agents.renewable_source_agent import (
    make_kaleo_solar_agent,
    make_keta_wind_agent,
    make_nzema_solar_agent,
)
from gridmind.agents.zone_agent import (
    make_accra_central_agent,
    make_kasoa_corridor_agent,
    make_kumasi_suame_agent,
    make_takoradi_harbour_agent,
    make_tema_industrial_agent,
)
from gridmind.config import (
    ACCRA_DR_JID,
    AGENT_PASSWORD,
    ECG_DISPATCH_JID,
    ECG_FORECAST_JID,
    GRIDCO_FAULT_JID,
    SIMULATION_TICKS,
    TICK_INTERVAL,
    DEMO_TICK_INTERVAL,
)
from gridmind.dashboard.ecg_terminal_dashboard import ECGTerminalDashboard
from gridmind.environment.ghana_grid_state import GhanaGridEnvironment
from gridmind.environment.scenarios import (
    SCENARIO_MAP,
    akosombo_curtailment,
    all_renewables_offline,
    gridco_line_trip,
    spintex_feeder_fault,
    tema_shift_change_spike,
)
from gridmind.evaluation.metrics_collector import MetricsCollector

SCENARIO_INJECT_TICK = 20
FULL_STRESS_SPACING = 30


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='GridMind — Ghana National Grid Multi-Agent Simulation',
    )
    parser.add_argument(
        '--demo-mode',
        action='store_true',
        help='Run in demo mode with slower tick interval (1.5s)',
    )
    parser.add_argument(
        '--scenario',
        choices=[
            'tema_spike', 'akosombo', 'spintex',
            'line_trip', 'all_offline', 'full_stress',
        ],
        default=None,
        help='Event scenario to inject during the simulation',
    )
    return parser.parse_args()


async def _inject_scenario(
    scenario_name: str,
    env: GhanaGridEnvironment,
    tick_interval: float,
) -> None:
    """Wait until the injection tick, then fire the selected scenario(s)."""
    await asyncio.sleep(SCENARIO_INJECT_TICK * tick_interval)

    if scenario_name == 'full_stress':
        ordered = [
            akosombo_curtailment,
            tema_shift_change_spike,
            spintex_feeder_fault,
            gridco_line_trip,
            all_renewables_offline,
        ]
        for fn in ordered:
            await fn(env)
            await asyncio.sleep(FULL_STRESS_SPACING * tick_interval)
    else:
        fn = SCENARIO_MAP[scenario_name]
        await fn(env)


async def main() -> None:
    args = _parse_args()
    demo_mode: bool = args.demo_mode
    tick_interval = DEMO_TICK_INTERVAL if demo_mode else TICK_INTERVAL

    env = GhanaGridEnvironment()
    metrics = MetricsCollector()
    dashboard = ECGTerminalDashboard()

    pw = AGENT_PASSWORD

    fault_watch = GRIDCoFaultWatchAgent(
        jid=GRIDCO_FAULT_JID, password=pw, env=env,
    )
    forecast_unit = ECGForecastUnitAgent(
        jid=ECG_FORECAST_JID, password=pw, env=env, demo_mode=demo_mode,
    )

    zone_agents = [
        make_tema_industrial_agent(env, pw, demo_mode),
        make_accra_central_agent(env, pw, demo_mode),
        make_kumasi_suame_agent(env, pw, demo_mode),
        make_kasoa_corridor_agent(env, pw, demo_mode),
        make_takoradi_harbour_agent(env, pw, demo_mode),
    ]

    renewable_agents = [
        make_kaleo_solar_agent(env, pw, demo_mode),
        make_nzema_solar_agent(env, pw, demo_mode),
        make_keta_wind_agent(env, pw, demo_mode),
    ]

    dr_agent = AccraIndustrialDRAgent(
        jid=ACCRA_DR_JID, password=pw, env=env, demo_mode=demo_mode,
    )
    dispatch_agent = ECGCentralDispatchAgent(
        jid=ECG_DISPATCH_JID, password=pw, env=env, demo_mode=demo_mode,
    )

    all_agents = [
        fault_watch,
        forecast_unit,
        *zone_agents,
        *renewable_agents,
        dr_agent,
        dispatch_agent,
    ]

    print('╔═══════════════════════════════════════════════════╗')
    print('║    GridMind — Ghana Grid Multi-Agent Simulation   ║')
    print(f'║    Mode: {"DEMO" if demo_mode else "STANDARD"}'
          f'  |  Ticks: {SIMULATION_TICKS}'
          f'  |  Interval: {tick_interval}s   ║')
    if args.scenario:
        print(f'║    Scenario: {args.scenario:<38}║')
    print('╚═══════════════════════════════════════════════════╝')
    print()

    print('[BOOT] Starting all 12 agents...')
    for agent in all_agents:
        await agent.start()
    print('[BOOT] All agents ONLINE.')

    metrics.start_recording(env)

    scenario_task = None
    if args.scenario:
        scenario_task = asyncio.create_task(
            _inject_scenario(args.scenario, env, tick_interval),
        )

    try:
        for _ in range(SIMULATION_TICKS):
            env.tick_forward()
            metrics.record_tick(env, dispatch_agent.beliefs)
            dashboard.render(env, dispatch_agent.beliefs, env.tick)
            await asyncio.sleep(tick_interval)

    except KeyboardInterrupt:
        print('\n[SHUTDOWN] Interrupt received — stopping gracefully...')

    finally:
        if scenario_task and not scenario_task.done():
            scenario_task.cancel()
            try:
                await scenario_task
            except asyncio.CancelledError:
                pass

        print('[SHUTDOWN] Stopping all agents...')
        for agent in reversed(all_agents):
            await agent.stop()
        print('[SHUTDOWN] All agents stopped.')

        print()
        metrics.print_report()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
