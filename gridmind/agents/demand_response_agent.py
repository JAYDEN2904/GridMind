"""
AccraIndustrialDRAgent — Demand Response agent for Accra's industrial consumers.

Manages a roster of large industrial consumers (VALCO, Tema Oil Refinery, etc.)
that have contracted to curtail load on request from ECG Central Dispatch.
When a REQUEST arrives, the agent negotiates with consumers in compliance-rate
order, simulates acceptance draws, and reports back with INFORM (success) or
FAILURE (shortfall) to the dispatch centre.
"""
from __future__ import annotations

import asyncio
import copy
import random

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour

from gridmind.communication.message_factory import build_message, parse_message
from gridmind.config import (
    ACCRA_DR_JID,
    ECG_DISPATCH_JID,
    DR_CONSUMER_ROSTER,
    TOTAL_DR_CONTRACTED_MW,
    TICK_INTERVAL,
    DEMO_TICK_INTERVAL,
)
from gridmind.environment.ghana_grid_state import GhanaGridEnvironment


class AccraIndustrialDRAgent(Agent):
    """Demand Response negotiation agent for Accra industrial consumers."""

    def __init__(
        self,
        jid: str,
        password: str,
        env: GhanaGridEnvironment,
        demo_mode: bool = False,
    ) -> None:
        super().__init__(jid, password)
        self.env = env
        self.demo_mode = demo_mode

        roster = copy.deepcopy(DR_CONSUMER_ROSTER)
        for consumer in roster.values():
            consumer['active'] = False

        self.beliefs: dict = {
            'consumer_roster': roster,
            'total_contracted_mw': TOTAL_DR_CONTRACTED_MW,
            'current_reduction_mw': 0.0,
            'pending_request': None,
            'history': [],
        }

    class HandleDRRequestBehaviour(CyclicBehaviour):
        """Receives DR REQUEST messages and negotiates load curtailment."""

        async def run(self) -> None:
            msg = await self.receive(timeout=2)
            if msg is None:
                return
            if msg.get_metadata('performative') != 'REQUEST':
                return

            agent: AccraIndustrialDRAgent = self.agent  # type: ignore[assignment]
            data = parse_message(msg)
            target_mw = data['target_reduction_mw']
            tick = data['tick']

            print(
                f"[ACCRA DR] 📋 DR REQUEST received: "
                f"need {target_mw} MW reduction"
            )

            agree_msg = build_message(
                to_jid=ECG_DISPATCH_JID,
                performative='AGREE',
                payload={
                    'acknowledged': True,
                    'target_mw': target_mw,
                    'tick': tick,
                },
                sender_jid=str(agent.jid),
                tick=tick,
            )
            await self.send(agree_msg)

            achieved_mw = 0.0
            engaged: list[dict] = []
            sorted_consumers = sorted(
                agent.beliefs['consumer_roster'].items(),
                key=lambda x: x[1]['compliance_rate'],
                reverse=True,
            )

            for consumer_id, data_c in sorted_consumers:
                if achieved_mw >= target_mw:
                    break
                accepted = random.random() < data_c['compliance_rate']
                if accepted:
                    reduction = min(
                        data_c['contracted_dr_mw'],
                        target_mw - achieved_mw,
                    )
                    achieved_mw += reduction
                    data_c['active'] = True
                    engaged.append({
                        'consumer': consumer_id,
                        'reduction_mw': reduction,
                        'compliance_rate': data_c['compliance_rate'],
                    })
                    print(
                        f"[ACCRA DR] ✅ {consumer_id}: "
                        f"-{reduction:.0f} MW agreed"
                    )
                else:
                    print(f"[ACCRA DR] ⚠ {consumer_id}: declined")

            agent.beliefs['current_reduction_mw'] = achieved_mw
            agent.beliefs['history'].append({
                'tick': tick,
                'target': target_mw,
                'achieved': achieved_mw,
                'consumers': engaged,
            })

            if achieved_mw >= target_mw * 0.90:
                result_msg = build_message(
                    to_jid=ECG_DISPATCH_JID,
                    performative='INFORM',
                    payload={
                        'achieved_mw': achieved_mw,
                        'target_mw': target_mw,
                        'consumers_engaged': engaged,
                        'tick': tick,
                        'success': True,
                    },
                    sender_jid=str(agent.jid),
                    tick=tick,
                )
                await self.send(result_msg)
                print(
                    f"[ACCRA DR] ✅ DR SUCCESS: {achieved_mw:.1f} MW shed "
                    f"from {len(engaged)} consumers"
                )
            else:
                gap = target_mw - achieved_mw
                failure_msg = build_message(
                    to_jid=ECG_DISPATCH_JID,
                    performative='FAILURE',
                    payload={
                        'achieved_mw': achieved_mw,
                        'gap_mw': gap,
                        'target_mw': target_mw,
                        'tick': tick,
                        'reason': 'roster_exhausted',
                    },
                    sender_jid=str(agent.jid),
                    tick=tick,
                )
                await self.send(failure_msg)
                print(
                    f"[ACCRA DR] ❌ DR SHORTFALL: achieved {achieved_mw:.1f} "
                    f"MW, gap = {gap:.1f} MW"
                )

            interval = DEMO_TICK_INTERVAL if agent.demo_mode else TICK_INTERVAL
            await asyncio.sleep(10 * interval)
            for c in agent.beliefs['consumer_roster'].values():
                c['active'] = False

    async def setup(self) -> None:
        handler = self.HandleDRRequestBehaviour()
        self.add_behaviour(handler)

        print(
            f"[ACCRA DR] DR Agent ONLINE — "
            f"{self.beliefs['total_contracted_mw']} MW contracted "
            f"across {len(self.beliefs['consumer_roster'])} consumers"
        )
