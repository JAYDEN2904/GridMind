"""
MetricsCollector — KPI recording and reporting for GridMind simulations.

Captures per-tick snapshots of grid state and computes aggregate KPIs
(dumsor frequency, renewable utilisation, DR success rate, response
latency) for comparison against the ECG baseline.
"""
from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

from gridmind.bdi.belief_base import ECGCentralDispatchBeliefs
from gridmind.config import DISTRICT_CONFIG, TOTAL_MANAGED_CAPACITY_MW
from gridmind.environment.ghana_grid_state import GhanaGridEnvironment


class MetricsCollector:
    """Records per-tick grid snapshots and generates aggregate KPI reports."""

    def __init__(self) -> None:
        self.tick_records: list[dict[str, Any]] = []
        self.start_tick: int = 0
        self.end_tick: int = 0
        self._audit_log_ref: list[dict[str, Any]] = []

    def start_recording(self, env: GhanaGridEnvironment) -> None:
        self.start_tick = env.tick

    def record_tick(
        self,
        env: GhanaGridEnvironment,
        beliefs: ECGCentralDispatchBeliefs,
    ) -> None:
        self.end_tick = env.tick
        self._audit_log_ref = beliefs.audit_log

        shedding = [
            d for d in DISTRICT_CONFIG
            if env.district_status.get(d) == 'shedding'
        ]
        shedding_per_district = {
            d: (1 if env.district_status.get(d) == 'shedding' else 0)
            for d in DISTRICT_CONFIG
        }

        injecting_mw = sum(
            env.renewable_available_mw.get(s, 0.0)
            for s in env.renewable_available_mw
            if env.renewable_injecting.get(s, False)
        )
        available_mw = sum(env.renewable_available_mw.values())

        self.tick_records.append({
            'tick': env.tick,
            'shedding_districts': len(shedding),
            'shedding_per_district': shedding_per_district,
            'total_demand_mw': env.get_total_demand(),
            'renewable_injecting_mw': injecting_mw,
            'renewable_available_mw': available_mw,
            'active_faults': len(beliefs.active_faults),
            'current_desire': beliefs.current_desire,
        })

    def generate_report(self) -> dict[str, Any]:
        if not self.tick_records:
            return {}

        dumsor_ticks = sum(
            1 for r in self.tick_records if r['shedding_districts'] > 0
        )

        shedding_duration: dict[str, int] = {d: 0 for d in DISTRICT_CONFIG}
        for record in self.tick_records:
            for d, val in record['shedding_per_district'].items():
                shedding_duration[d] += val

        total_injected = sum(r['renewable_injecting_mw'] for r in self.tick_records)
        total_available = sum(r['renewable_available_mw'] for r in self.tick_records)
        renewable_util = (
            total_injected / total_available if total_available > 0 else 0.0
        )

        peak_util = max(
            r['total_demand_mw'] / TOTAL_MANAGED_CAPACITY_MW
            for r in self.tick_records
        )

        avg_latency = self._compute_response_latency()
        dr_success = self._compute_dr_success_rate()

        return {
            'total_ticks': len(self.tick_records),
            'dumsor_frequency': dumsor_ticks,
            'shedding_duration_per_district': shedding_duration,
            'renewable_utilisation_pct': renewable_util,
            'average_response_latency': avg_latency,
            'dr_success_rate': dr_success,
            'peak_utilisation_pct': peak_util,
        }

    def _compute_response_latency(self) -> float:
        fault_ticks: list[int] = []
        action_ticks: list[int] = []

        for entry in self._audit_log_ref:
            if entry.get('event_type') in ('demand_spike', 'feeder_loss'):
                fault_ticks.append(entry.get('tick', 0))
            event = entry.get('event', '')
            if event in ('INTENTION_RECONSIDERATION', 'DUMSOR_ROTATION'):
                action_ticks.append(entry.get('tick', 0))

        if not fault_ticks or not action_ticks:
            return 0.0

        latencies: list[int] = []
        for ft in fault_ticks:
            later_actions = [at for at in action_ticks if at >= ft]
            if later_actions:
                latencies.append(min(later_actions) - ft)

        return sum(latencies) / len(latencies) if latencies else 0.0

    def _compute_dr_success_rate(self) -> float:
        successes = 0
        failures = 0
        for entry in self._audit_log_ref:
            reason = str(entry.get('reason', ''))
            if 'DR completed' in reason:
                successes += 1
            elif 'DR failed' in reason:
                failures += 1
        total = successes + failures
        return successes / total if total > 0 else 0.0

    def print_report(self) -> None:
        report = self.generate_report()
        if not report:
            print('No metrics recorded.')
            return

        console = Console()
        console.print()

        table = Table(title='GridMind Simulation KPI Report', expand=True)
        table.add_column('Metric', min_width=35)
        table.add_column('Value', justify='right')

        table.add_row(
            'Total Simulation Ticks',
            str(report['total_ticks']),
        )
        table.add_row(
            'Dumsor Frequency (ticks with shedding)',
            str(report['dumsor_frequency']),
        )
        table.add_row(
            'Peak Utilisation',
            f"{report['peak_utilisation_pct']:.1%}",
        )
        table.add_row(
            'Renewable Utilisation',
            f"{report['renewable_utilisation_pct']:.1%}",
        )
        table.add_row(
            'Average Response Latency (ticks)',
            f"{report['average_response_latency']:.1f}",
        )
        table.add_row(
            'DR Success Rate',
            f"{report['dr_success_rate']:.1%}",
        )

        console.print(table)

        shed_table = Table(title='Shedding Duration per District')
        shed_table.add_column('District')
        shed_table.add_column('Ticks Shed', justify='right')
        for district, ticks in report['shedding_duration_per_district'].items():
            shed_table.add_row(district, str(ticks))
        console.print(shed_table)
