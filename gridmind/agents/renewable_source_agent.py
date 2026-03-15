"""
RenewableSourceAgent — deliberative-reactive hybrid for Ghana's renewable plants.

Each instance models one of three real renewable sources: Kaleo Solar (155 MW),
Nzema Solar (20 MW), or Keta Wind (50 MW).  Capacity varies with a simulated
time-of-day curve.  The agent responds to CFP messages from ECG Central
Dispatch as part of the FIPA Contract Net Protocol.
"""
from __future__ import annotations

import random

from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, CyclicBehaviour

from gridmind.config import (
    ECG_DISPATCH_JID,
    KALEO_SOLAR_JID,
    NZEMA_SOLAR_JID,
    KETA_WIND_JID,
    RENEWABLE_CONFIG,
    TICK_INTERVAL,
    DEMO_TICK_INTERVAL,
)
from gridmind.communication.message_factory import build_message, parse_message
from gridmind.environment.ghana_grid_state import GhanaGridEnvironment


def _solar_time_factor(tick: int) -> float:
    """Map tick within a 48-tick day cycle to a solar irradiance factor [0, 1]."""
    t = tick % 48
    if t <= 8:
        return 0.0
    if t <= 15:
        return (t - 8) / 7.0
    if t <= 24:
        return 1.0
    if t <= 31:
        return 1.0 - (t - 24) / 7.0
    return 0.0


class RenewableSourceAgent(Agent):
    """Hybrid agent for a single renewable generation source."""

    def __init__(
        self,
        jid: str,
        password: str,
        source_id: str,
        env: GhanaGridEnvironment,
        max_capacity_mw: float,
        cost_coeff: float,
        source_type: str,
        demo_mode: bool = False,
    ) -> None:
        super().__init__(jid, password)
        self.source_id = source_id
        self.env = env
        self.source_type = source_type
        self.demo_mode = demo_mode
        self.beliefs: dict = {
            'source_id': source_id,
            'installed_mw': max_capacity_mw,
            'available_mw': 0.0,
            'cost_coeff': cost_coeff,
            'weather_factor': 1.0,
            'time_of_day_factor': 0.0,
            'currently_injecting': False,
            'injecting_mw': 0.0,
        }

    # ── Behaviour 1: Capacity model update ───────────────────────

    class UpdateCapacityBehaviour(PeriodicBehaviour):
        """Recomputes available MW based on time-of-day and weather."""

        async def run(self) -> None:
            agent: RenewableSourceAgent = self.agent  # type: ignore[assignment]
            beliefs = agent.beliefs
            tick = agent.env.tick
            installed = beliefs['installed_mw']
            weather = beliefs['weather_factor']

            solar_factor = _solar_time_factor(tick)

            if agent.source_type == 'solar':
                tod_factor = solar_factor
            else:
                tod_factor = (1.0 - solar_factor) * random.uniform(0.7, 1.0)

            beliefs['time_of_day_factor'] = tod_factor
            available = installed * weather * tod_factor
            beliefs['available_mw'] = available
            agent.env.renewable_available_mw[agent.source_id] = available

    # ── Behaviour 2: CFP / ACCEPT / REJECT handling ──────────────

    class ReceiveCFPBehaviour(CyclicBehaviour):
        """Responds to Contract Net Protocol messages from ECG Dispatch."""

        async def run(self) -> None:
            msg = await self.receive(timeout=2)
            if msg is None:
                return

            agent: RenewableSourceAgent = self.agent  # type: ignore[assignment]
            beliefs = agent.beliefs
            data = parse_message(msg)
            performative = msg.get_metadata('performative')
            sender_jid = str(agent.jid)

            if performative == 'CFP':
                available = beliefs['available_mw']
                if available > 5.0 and not beliefs['currently_injecting']:
                    propose_msg = build_message(
                        to_jid=ECG_DISPATCH_JID,
                        performative='PROPOSE',
                        payload={
                            'source': beliefs['source_id'],
                            'available_mw': round(available, 2),
                            'cost_coeff': beliefs['cost_coeff'],
                            'conversation_id': data.get('conversation_id'),
                        },
                        sender_jid=sender_jid,
                        tick=agent.env.tick,
                        conversation_id=data.get('conversation_id'),
                    )
                    await self.send(propose_msg)
                    print(
                        f"[{beliefs['source_id']}] 📤 PROPOSE: "
                        f"{available:.1f} MW @ {beliefs['cost_coeff']}"
                    )
                else:
                    reason = (
                        'currently_injecting'
                        if beliefs['currently_injecting']
                        else 'insufficient_capacity'
                    )
                    refuse_msg = build_message(
                        to_jid=ECG_DISPATCH_JID,
                        performative='REFUSE',
                        payload={
                            'source': beliefs['source_id'],
                            'reason': reason,
                            'available_mw': round(available, 2),
                            'conversation_id': data.get('conversation_id'),
                        },
                        sender_jid=sender_jid,
                        tick=agent.env.tick,
                        conversation_id=data.get('conversation_id'),
                    )
                    await self.send(refuse_msg)
                    print(f"[{beliefs['source_id']}] ❌ REFUSE: {reason}")

            elif performative == 'ACCEPT-PROPOSAL':
                accepted_mw = min(
                    data.get('accepted_mw', beliefs['available_mw']),
                    beliefs['available_mw'],
                )
                beliefs['currently_injecting'] = True
                beliefs['injecting_mw'] = accepted_mw
                beliefs['available_mw'] -= accepted_mw
                agent.env.renewable_injecting[agent.source_id] = True

                confirm_msg = build_message(
                    to_jid=ECG_DISPATCH_JID,
                    performative='INFORM',
                    payload={
                        'source': beliefs['source_id'],
                        'injecting_mw': round(accepted_mw, 2),
                        'confirmed': True,
                    },
                    sender_jid=sender_jid,
                    tick=agent.env.tick,
                    conversation_id=data.get('conversation_id'),
                )
                await self.send(confirm_msg)
                print(
                    f"[{beliefs['source_id']}] ⚡ INJECTING "
                    f"{accepted_mw:.1f} MW into Ghana grid"
                )

            elif performative == 'REJECT-PROPOSAL':
                print(
                    f"[{beliefs['source_id']}] Proposal rejected "
                    f"— capacity retained"
                )

    # ── Agent setup ──────────────────────────────────────────────

    async def setup(self) -> None:
        period = DEMO_TICK_INTERVAL if self.demo_mode else TICK_INTERVAL
        capacity_update = self.UpdateCapacityBehaviour(period=period)
        self.add_behaviour(capacity_update)

        receive_cfp = self.ReceiveCFPBehaviour()
        self.add_behaviour(receive_cfp)

        print(
            f"[{self.source_id}] Renewable agent started — "
            f"{self.beliefs['installed_mw']} MW {self.source_type} "
            f"(cost coeff {self.beliefs['cost_coeff']})"
        )


# ── Factory functions for each Ghana renewable source ────────────


def make_kaleo_solar_agent(
    env: GhanaGridEnvironment, password: str, demo_mode: bool = False,
) -> RenewableSourceAgent:
    cfg = RENEWABLE_CONFIG['kaleo_solar']
    return RenewableSourceAgent(
        jid=KALEO_SOLAR_JID, password=password,
        source_id='kaleo_solar', env=env,
        max_capacity_mw=cfg['max_capacity_mw'],
        cost_coeff=cfg['cost_coeff'],
        source_type='solar', demo_mode=demo_mode,
    )


def make_nzema_solar_agent(
    env: GhanaGridEnvironment, password: str, demo_mode: bool = False,
) -> RenewableSourceAgent:
    cfg = RENEWABLE_CONFIG['nzema_solar']
    return RenewableSourceAgent(
        jid=NZEMA_SOLAR_JID, password=password,
        source_id='nzema_solar', env=env,
        max_capacity_mw=cfg['max_capacity_mw'],
        cost_coeff=cfg['cost_coeff'],
        source_type='solar', demo_mode=demo_mode,
    )


def make_keta_wind_agent(
    env: GhanaGridEnvironment, password: str, demo_mode: bool = False,
) -> RenewableSourceAgent:
    cfg = RENEWABLE_CONFIG['keta_wind']
    return RenewableSourceAgent(
        jid=KETA_WIND_JID, password=password,
        source_id='keta_wind', env=env,
        max_capacity_mw=cfg['max_capacity_mw'],
        cost_coeff=cfg['cost_coeff'],
        source_type='wind', demo_mode=demo_mode,
    )
