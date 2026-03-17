"""
ECG Baseline Runner — simple threshold-based shedding without agents.

Provides a no-agent baseline for KPI comparison: the same scenario runs
through a pure-Python loop that sheds kasoa_corridor at 90% utilisation
and accra_central at 95%.  No renewable procurement or demand response
is attempted.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from rich.console import Console
from rich.table import Table

from gridmind.config import (
    DISTRICT_CONFIG,
    TOTAL_MANAGED_CAPACITY_MW,
    TICK_INTERVAL,
)
from gridmind.environment.ghana_grid_state import GhanaGridEnvironment


async def run_baseline(
    scenario_fn: Callable[[GhanaGridEnvironment], Coroutine[Any, Any, None]],
    ticks: int = 200,
) -> dict[str, Any]:
    """Run a scenario with naive threshold shedding and return KPIs.

    This baseline uses no agents — just a loop that checks total demand
    each tick and sheds districts by fixed threshold rules.
    """
    env = GhanaGridEnvironment()

    scenario_task = asyncio.create_task(scenario_fn(env))

    records: list[dict[str, Any]] = []

    for _ in range(ticks):
        env.tick_forward()
        total_demand = env.get_total_demand()

        for d in DISTRICT_CONFIG:
            env.district_status[d] = 'normal'

        if total_demand > TOTAL_MANAGED_CAPACITY_MW * 0.95:
            env.district_status['kasoa_corridor'] = 'shedding'
            env.district_status['accra_central'] = 'shedding'
        elif total_demand > TOTAL_MANAGED_CAPACITY_MW * 0.90:
            env.district_status['kasoa_corridor'] = 'shedding'

        shedding_per_district = {
            d: (1 if env.district_status.get(d) == 'shedding' else 0)
            for d in DISTRICT_CONFIG
        }
        shedding_count = sum(shedding_per_district.values())

        records.append({
            'tick': env.tick,
            'shedding_districts': shedding_count,
            'shedding_per_district': shedding_per_district,
            'total_demand_mw': total_demand,
            'renewable_injecting_mw': 0.0,
            'renewable_available_mw': sum(env.renewable_available_mw.values()),
        })

        await asyncio.sleep(TICK_INTERVAL)

    if not scenario_task.done():
        scenario_task.cancel()
        try:
            await scenario_task
        except asyncio.CancelledError:
            pass

    dumsor_ticks = sum(1 for r in records if r['shedding_districts'] > 0)

    shedding_duration: dict[str, int] = {d: 0 for d in DISTRICT_CONFIG}
    for record in records:
        for d, val in record['shedding_per_district'].items():
            shedding_duration[d] += val

    total_available = sum(r['renewable_available_mw'] for r in records)

    peak_util = max(
        r['total_demand_mw'] / TOTAL_MANAGED_CAPACITY_MW for r in records
    )

    return {
        'total_ticks': len(records),
        'dumsor_frequency': dumsor_ticks,
        'shedding_duration_per_district': shedding_duration,
        'renewable_utilisation_pct': 0.0,
        'average_response_latency': 0.0,
        'dr_success_rate': 0.0,
        'peak_utilisation_pct': peak_util,
    }


def print_baseline_report(report: dict[str, Any]) -> None:
    """Format and print baseline KPIs using Rich."""
    console = Console()
    console.print()

    table = Table(title='ECG Baseline KPI Report (No Agents)', expand=True)
    table.add_column('Metric', min_width=35)
    table.add_column('Value', justify='right')

    table.add_row('Total Simulation Ticks', str(report['total_ticks']))
    table.add_row(
        'Dumsor Frequency (ticks with shedding)',
        str(report['dumsor_frequency']),
    )
    table.add_row('Peak Utilisation', f"{report['peak_utilisation_pct']:.1%}")
    table.add_row(
        'Renewable Utilisation',
        f"{report['renewable_utilisation_pct']:.1%}",
    )
    table.add_row(
        'Average Response Latency (ticks)',
        f"{report['average_response_latency']:.1f}",
    )
    table.add_row('DR Success Rate', f"{report['dr_success_rate']:.1%}")

    console.print(table)

    shed_table = Table(title='Baseline Shedding Duration per District')
    shed_table.add_column('District')
    shed_table.add_column('Ticks Shed', justify='right')
    for district, ticks_shed in report['shedding_duration_per_district'].items():
        shed_table.add_row(district, str(ticks_shed))
    console.print(shed_table)


def print_side_by_side_report(
    mas_report: dict[str, Any],
    baseline_report: dict[str, Any],
) -> None:
    """Print a side-by-side comparison between MAS and baseline KPIs."""
    console = Console()
    console.print()

    table = Table(title='GridMind vs ECG Baseline KPI Comparison', expand=True)
    table.add_column('Metric', min_width=35)
    table.add_column('MAS', justify='right')
    table.add_column('Baseline', justify='right')

    def _fmt_pct(value: float) -> str:
        return f"{value:.1%}"

    table.add_row(
        'Total Simulation Ticks',
        str(mas_report.get('total_ticks', '')),
        str(baseline_report.get('total_ticks', '')),
    )
    table.add_row(
        'Dumsor Frequency (ticks with shedding)',
        str(mas_report.get('dumsor_frequency', '')),
        str(baseline_report.get('dumsor_frequency', '')),
    )
    table.add_row(
        'Peak Utilisation',
        _fmt_pct(mas_report.get('peak_utilisation_pct', 0.0)),
        _fmt_pct(baseline_report.get('peak_utilisation_pct', 0.0)),
    )
    table.add_row(
        'Renewable Utilisation',
        _fmt_pct(mas_report.get('renewable_utilisation_pct', 0.0)),
        _fmt_pct(baseline_report.get('renewable_utilisation_pct', 0.0)),
    )
    table.add_row(
        'Average Response Latency (ticks)',
        f"{mas_report.get('average_response_latency', 0.0):.1f}",
        f"{baseline_report.get('average_response_latency', 0.0):.1f}",
    )
    table.add_row(
        'DR Success Rate',
        _fmt_pct(mas_report.get('dr_success_rate', 0.0)),
        _fmt_pct(baseline_report.get('dr_success_rate', 0.0)),
    )
    table.add_row(
        'Forecast Accuracy',
        _fmt_pct(mas_report.get('forecast_accuracy', 0.0)),
        _fmt_pct(baseline_report.get('forecast_accuracy', 0.0)),
    )

    console.print(table)


if __name__ == '__main__':
    # Example standalone baseline run for Akosombo low-water scenario.
    from gridmind.environment.scenarios import akosombo_curtailment

    async def _main() -> None:
        report = await run_baseline(akosombo_curtailment)
        print_baseline_report(report)

    asyncio.run(_main())
