"""
DistrictZoneAgent — reactive sensor agent for each ECG distribution district.

Each instance monitors one of Ghana's five modelled districts, reads the
current demand from the shared environment, applies sensor noise, and
sends INFORM messages to ECG Central Dispatch, GRIDCo Fault Watch, and
the ECG Forecast Unit every tick.  No deliberation, no goals — pure
sense-act reactive behaviour.
"""
from __future__ import annotations

import numpy as np
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, CyclicBehaviour

from gridmind.config import (
    DISTRICT_CONFIG,
    SENSOR_NOISE_FACTOR,
    TICK_INTERVAL,
    DEMO_TICK_INTERVAL,
    ECG_DISPATCH_JID,
    GRIDCO_FAULT_JID,
    ECG_FORECAST_JID,
    TEMA_INDUSTRIAL_JID,
    ACCRA_CENTRAL_JID,
    KUMASI_SUAME_JID,
    KASOA_CORRIDOR_JID,
    TAKORADI_HARBOUR_JID,
)
from gridmind.communication.message_factory import build_message, parse_message
from gridmind.environment.ghana_grid_state import GhanaGridEnvironment


class DistrictZoneAgent(Agent):
    """Reactive agent that senses district demand and reports to ECG/GRIDCo."""

    def __init__(
        self,
        jid: str,
        password: str,
        district_id: str,
        env: GhanaGridEnvironment,
        demo_mode: bool = False,
    ) -> None:
        super().__init__(jid, password)
        self.district_id = district_id
        self.env = env
        self.demo_mode = demo_mode
        self.beliefs: dict = {
            'district_id': district_id,
            'current_mw': 0.0,
            'capacity_mw': DISTRICT_CONFIG[district_id]['ceiling_mw'],
            'utilisation_pct': 0.0,
            'last_5_readings': [],
            'trend': 'stable',
            'status': 'normal',
        }

    class ReadAndReportBehaviour(PeriodicBehaviour):
        """Periodic sense-act loop: read demand, add noise, report."""

        async def run(self) -> None:
            agent: DistrictZoneAgent = self.agent  # type: ignore[assignment]
            district_id = agent.district_id
            env = agent.env
            beliefs = agent.beliefs

            raw_reading = env.district_demand_mw[district_id]
            noise = np.random.normal(0, raw_reading * SENSOR_NOISE_FACTOR[district_id])
            noisy_reading = max(0.0, raw_reading + noise)

            capacity_mw = beliefs['capacity_mw']
            utilisation_pct = noisy_reading / capacity_mw if capacity_mw > 0 else 0.0

            beliefs['current_mw'] = noisy_reading
            beliefs['utilisation_pct'] = utilisation_pct

            readings = beliefs['last_5_readings']
            readings.append(noisy_reading)
            if len(readings) > 5:
                readings.pop(0)

            if len(readings) >= 2:
                slope = readings[-1] - readings[0]
                if slope > 2.0:
                    beliefs['trend'] = 'rising'
                elif slope < -2.0:
                    beliefs['trend'] = 'falling'
                else:
                    beliefs['trend'] = 'stable'

            payload = {
                'district': district_id,
                'demand_mw': noisy_reading,
                'capacity_mw': capacity_mw,
                'trend': beliefs['trend'],
                'utilisation_pct': utilisation_pct,
            }
            sender_jid = str(agent.jid)

            msg_dispatch = build_message(
                to_jid=ECG_DISPATCH_JID,
                performative='INFORM',
                payload=payload,
                sender_jid=sender_jid,
                tick=env.tick,
            )
            await self.send(msg_dispatch)

            msg_fault = build_message(
                to_jid=GRIDCO_FAULT_JID,
                performative='INFORM',
                payload=payload,
                sender_jid=sender_jid,
                tick=env.tick,
            )
            await self.send(msg_fault)

            msg_forecast = build_message(
                to_jid=ECG_FORECAST_JID,
                performative='INFORM',
                payload=payload,
                sender_jid=sender_jid,
                tick=env.tick,
            )
            await self.send(msg_forecast)

            print(
                f"[{district_id}] {noisy_reading:.1f} MW "
                f"/ {capacity_mw} MW ({utilisation_pct:.1%}) "
                f"[{beliefs['trend']}]"
            )

    class ReceiveBroadcastBehaviour(CyclicBehaviour):
        """Listens for system-wide broadcast messages from ECG Central Dispatch."""

        async def run(self) -> None:
            msg = await self.receive(timeout=1)
            if msg is None:
                return
            agent: DistrictZoneAgent = self.agent  # type: ignore[assignment]
            data = parse_message(msg)
            new_status = data.get('status', agent.beliefs['status'])
            agent.beliefs['status'] = new_status
            print(f"[{agent.district_id}] System status received: {new_status}")

    async def setup(self) -> None:
        period = DEMO_TICK_INTERVAL if self.demo_mode else TICK_INTERVAL
        read_report = self.ReadAndReportBehaviour(period=period)
        self.add_behaviour(read_report)

        recv_broadcast = self.ReceiveBroadcastBehaviour()
        self.add_behaviour(recv_broadcast)

        print(f"[{self.district_id}] Zone agent started — "
              f"capacity {self.beliefs['capacity_mw']} MW")


# ── Factory functions for each Ghana district ────────────────────


def make_tema_industrial_agent(
    env: GhanaGridEnvironment, password: str, demo_mode: bool = False,
) -> DistrictZoneAgent:
    return DistrictZoneAgent(
        jid=TEMA_INDUSTRIAL_JID, password=password,
        district_id='tema_industrial', env=env, demo_mode=demo_mode,
    )


def make_accra_central_agent(
    env: GhanaGridEnvironment, password: str, demo_mode: bool = False,
) -> DistrictZoneAgent:
    return DistrictZoneAgent(
        jid=ACCRA_CENTRAL_JID, password=password,
        district_id='accra_central', env=env, demo_mode=demo_mode,
    )


def make_kumasi_suame_agent(
    env: GhanaGridEnvironment, password: str, demo_mode: bool = False,
) -> DistrictZoneAgent:
    return DistrictZoneAgent(
        jid=KUMASI_SUAME_JID, password=password,
        district_id='kumasi_suame', env=env, demo_mode=demo_mode,
    )


def make_kasoa_corridor_agent(
    env: GhanaGridEnvironment, password: str, demo_mode: bool = False,
) -> DistrictZoneAgent:
    return DistrictZoneAgent(
        jid=KASOA_CORRIDOR_JID, password=password,
        district_id='kasoa_corridor', env=env, demo_mode=demo_mode,
    )


def make_takoradi_harbour_agent(
    env: GhanaGridEnvironment, password: str, demo_mode: bool = False,
) -> DistrictZoneAgent:
    return DistrictZoneAgent(
        jid=TAKORADI_HARBOUR_JID, password=password,
        district_id='takoradi_harbour', env=env, demo_mode=demo_mode,
    )
