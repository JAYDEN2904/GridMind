"""
ECGTerminalDashboard — Rich-based live terminal display for GridMind.

Renders a five-panel view every simulation tick showing grid status,
district demands, BDI state, renewable injection, and audit-log tail.
"""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from gridmind.bdi.belief_base import ECGCentralDispatchBeliefs
from gridmind.config import (
    DISTRICT_CONFIG,
    DISTRICT_DISPLAY_NAMES,
    DISTRICT_CAPACITY,
    RENEWABLE_CONFIG,
    TOTAL_MANAGED_CAPACITY_MW,
)
from gridmind.environment.ghana_grid_state import GhanaGridEnvironment

_RENEWABLE_DISPLAY = {
    'kaleo_solar': 'Kaleo Solar',
    'nzema_solar': 'Nzema Solar',
    'keta_wind': 'Keta Wind',
}

_STATUS_COLOUR = {
    'normal': 'green',
    'warning': 'yellow',
    'shedding': 'red',
    'fault': 'bright_black',
}

_DESIRE_COLOUR = {
    'MONITOR': 'green',
    'OPTIMISE_RENEWABLES': 'green',
    'PREEMPTIVE_RESPONSE': 'yellow',
    'RESPOND_TO_FAULT': 'dark_orange',
    'EMERGENCY_STABILISE': 'bold red',
}


class ECGTerminalDashboard:
    """Five-panel Rich console dashboard for the GridMind simulation."""

    def __init__(self) -> None:
        self.console = Console()
        self._prev_demands: dict[str, float] = {}

    def render(
        self,
        env: GhanaGridEnvironment,
        beliefs: ECGCentralDispatchBeliefs,
        tick: int,
    ) -> None:
        self.console.clear()
        self.console.print(self._header(env, tick))
        self.console.print(self._district_table(env))
        self.console.print(self._bdi_panel(beliefs))
        self.console.print(self._renewable_panel(env))
        self.console.print(self._audit_panel(beliefs))

        self._prev_demands = dict(env.district_demand_mw)

    # ── Panel 1: Grid Status Header ──────────────────────────

    def _header(self, env: GhanaGridEnvironment, tick: int) -> Panel:
        total_mw = env.get_total_demand()
        utilisation = env.get_utilisation_pct()

        if utilisation > 0.98:
            colour = 'bold red'
        elif utilisation > 0.85:
            colour = 'red'
        elif utilisation > 0.70:
            colour = 'yellow'
        else:
            colour = 'green'

        header = Text()
        header.append('⚡ GridMind — ECG & GRIDCo Proof-of-Concept')
        header.append(f'  |  Tick: {tick}')
        header.append(f'  |  Total Load: {total_mw:.0f} MW / '
                       f'{TOTAL_MANAGED_CAPACITY_MW:.0f} MW (')
        header.append(f'{utilisation:.1%}', style=colour)
        header.append(')')
        return Panel(header, title='Grid Status')

    # ── Panel 2: District Status Table ───────────────────────

    def _district_table(self, env: GhanaGridEnvironment) -> Panel:
        table = Table(expand=True)
        table.add_column('District', min_width=28)
        table.add_column('Demand (MW)', justify='right')
        table.add_column('Ceiling (MW)', justify='right')
        table.add_column('Util%', justify='right')
        table.add_column('Trend', justify='center')
        table.add_column('Status', justify='center')

        for district in DISTRICT_CONFIG:
            demand = env.district_demand_mw.get(district, 0.0)
            ceiling = DISTRICT_CAPACITY[district]
            util = demand / ceiling if ceiling > 0 else 0.0
            status = env.district_status.get(district, 'normal')
            colour = _STATUS_COLOUR.get(status, 'white')

            prev = self._prev_demands.get(district)
            if prev is not None:
                delta = demand - prev
                if delta > 2.0:
                    trend = '↑ rising'
                elif delta < -2.0:
                    trend = '↓ falling'
                else:
                    trend = '→ stable'
            else:
                trend = '--'

            display_name = DISTRICT_DISPLAY_NAMES.get(district, district)
            table.add_row(
                Text(display_name, style=colour),
                Text(f'{demand:.1f}', style=colour),
                Text(f'{ceiling:.0f}', style=colour),
                Text(f'{util:.1%}', style=colour),
                Text(trend, style=colour),
                Text(status.upper(), style=colour),
            )

        return Panel(table, title='District Status')

    # ── Panel 3: BDI State ───────────────────────────────────

    @staticmethod
    def _bdi_panel(beliefs: ECGCentralDispatchBeliefs) -> Panel:
        desire = beliefs.current_desire
        intention = beliefs.current_intention
        faults = beliefs.active_faults

        content = Text()
        content.append('Current Desire:    ')
        content.append(desire, style=_DESIRE_COLOUR.get(desire, 'white'))
        content.append('\nCurrent Intention: ')
        content.append(intention)
        content.append('\nActive Faults:     ')
        content.append(', '.join(faults) if faults else 'None')
        content.append('\nDR Active:         ')
        content.append(
            'Yes' if beliefs.demand_response_active else 'No',
            style='red' if beliefs.demand_response_active else 'green',
        )

        return Panel(content, title='ECG Central Dispatch — BDI State')

    # ── Panel 4: Renewable Status ────────────────────────────

    @staticmethod
    def _renewable_panel(env: GhanaGridEnvironment) -> Panel:
        table = Table(expand=True)
        table.add_column('Source', min_width=16)
        table.add_column('Available (MW)', justify='right')
        table.add_column('Injecting', justify='center')
        table.add_column('Installed (MW)', justify='right')

        for source_id, cfg in RENEWABLE_CONFIG.items():
            avail = env.renewable_available_mw.get(source_id, 0.0)
            injecting = env.renewable_injecting.get(source_id, False)
            installed = cfg['max_capacity_mw']
            inj_text = Text('YES', style='green') if injecting else Text(
                'no', style='bright_black',
            )
            display = _RENEWABLE_DISPLAY.get(source_id, source_id)
            table.add_row(display, f'{avail:.1f}', inj_text, f'{installed:.0f}')

        return Panel(table, title='Renewable Status')

    # ── Panel 5: Audit Log Tail ──────────────────────────────

    @staticmethod
    def _audit_panel(beliefs: ECGCentralDispatchBeliefs) -> Panel:
        entries = beliefs.audit_log[-5:] if beliefs.audit_log else []
        if not entries:
            return Panel(Text('No audit entries yet.', style='bright_black'),
                         title='Audit Log (last 5)')

        table = Table(expand=True)
        table.add_column('Tick', justify='right', width=6)
        table.add_column('Event')
        table.add_column('Detail')

        for entry in entries:
            tick_val = str(entry.get('tick', ''))
            event = entry.get('event', entry.get('event_type',
                              entry.get('belief_updated', '--')))
            reason = entry.get('reason', entry.get('reason_chain',
                              entry.get('detail', '')))
            if len(str(reason)) > 80:
                reason = str(reason)[:77] + '...'
            table.add_row(tick_val, str(event), str(reason))

        return Panel(table, title='Audit Log (last 5)')
