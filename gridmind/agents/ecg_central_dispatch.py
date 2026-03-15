"""
ECGCentralDispatchAgent — the BDI centrepiece of GridMind.

Models ECG's Central Dispatch Centre with full Beliefs-Desires-Intentions
architecture.  Four concurrent behaviours run in parallel:

  BDILoopBehaviour           — deliberation cycle with intention reconsideration
  ReceiveAndUpdateBelief     — percept processing and belief revision
  BroadcastBehaviour         — periodic system-status broadcast to all districts
  ExecuteIntentionBehaviour  — executes the active plan (CNP, DR escalation)

This agent demonstrates explicit intention reconsideration: when a
higher-priority desire activates mid-plan, the switch is logged with
full context (from_desire, to_desire, tick, reason).
"""
from __future__ import annotations

import asyncio

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour

from gridmind.bdi.belief_base import ECGCentralDispatchBeliefs
from gridmind.bdi.desire_evaluator import evaluate_desires
from gridmind.bdi.intention_selector import select_intention, has_desire_changed
from gridmind.communication.contract_net import initiate_contract_net
from gridmind.communication.message_factory import build_message, parse_message
from gridmind.config import (
    ECG_DISPATCH_JID,
    GRIDCO_FAULT_JID,
    ECG_FORECAST_JID,
    ACCRA_DR_JID,
    KALEO_SOLAR_JID,
    NZEMA_SOLAR_JID,
    KETA_WIND_JID,
    DISTRICT_JIDS,
    RENEWABLE_JIDS,
    TICK_INTERVAL,
    DEMO_TICK_INTERVAL,
    BROADCAST_INTERVAL,
    SHEDDING_ORDER,
    DISTRICT_CAPACITY,
)
from gridmind.environment.ghana_grid_state import GhanaGridEnvironment


class ECGCentralDispatchAgent(Agent):
    """Full BDI agent modelling ECG's Central Dispatch Centre."""

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
        self.beliefs = ECGCentralDispatchBeliefs()
        self.current_desire: str = 'MONITOR'
        self.current_intention: str = 'passive_monitoring'
        self.dr_execution_pending: bool = False

    # ── Behaviour 1: BDI deliberation loop ───────────────────────

    class BDILoopBehaviour(CyclicBehaviour):
        """Evaluates desires, selects intentions, and handles reconsideration."""

        async def run(self) -> None:
            agent: ECGCentralDispatchAgent = self.agent  # type: ignore[assignment]
            beliefs = agent.beliefs
            tick = agent.env.tick

            new_desire = evaluate_desires(beliefs)

            if has_desire_changed(agent.current_desire, new_desire):
                old_desire = agent.current_desire
                old_intention = agent.current_intention
                new_intention = select_intention(new_desire)

                beliefs.audit_log.append({
                    'tick': tick,
                    'agent': 'ecg_central_dispatch',
                    'event': 'INTENTION_RECONSIDERATION',
                    'from_desire': old_desire,
                    'to_desire': new_desire,
                    'from_intention': old_intention,
                    'to_intention': new_intention,
                    'reason_chain': (
                        f"Desire changed from {old_desire} to {new_desire} "
                        f"at tick {tick}; intention switched from "
                        f"{old_intention} to {new_intention}"
                    ),
                })

                agent.current_desire = new_desire
                agent.current_intention = new_intention

                beliefs.update(
                    'current_desire', new_desire,
                    f"BDI reconsideration: {old_desire} -> {new_desire}",
                    tick,
                )
                beliefs.update(
                    'current_intention', new_intention,
                    f"Intention follows desire: {new_intention}",
                    tick,
                )

                print(
                    f"[ECG DISPATCH] 🔄 RECONSIDERATION: "
                    f"{old_desire} → {new_desire} | "
                    f"intention: {old_intention} → {new_intention}"
                )

            interval = DEMO_TICK_INTERVAL if agent.demo_mode else TICK_INTERVAL
            await asyncio.sleep(interval)

    # ── Behaviour 2: Message reception and belief revision ───────

    class ReceiveAndUpdateBelief(CyclicBehaviour):
        """Processes incoming percepts and revises the belief base."""

        async def run(self) -> None:
            msg = await self.receive(timeout=2)
            if msg is None:
                return

            agent: ECGCentralDispatchAgent = self.agent  # type: ignore[assignment]
            beliefs = agent.beliefs
            data = parse_message(msg)
            performative = msg.get_metadata('performative')
            sender = data.get('sender', '')
            tick = data.get('tick', agent.env.tick)

            if performative == 'INFORM':
                self._handle_inform(agent, beliefs, data, sender, tick)

            elif performative == 'PROPOSE':
                if data.get('conversation_id') == beliefs.pending_cnp_id:
                    beliefs.pending_cnp_proposals.append(data)
                    print(
                        f"[ECG DISPATCH] 📋 PROPOSAL received: "
                        f"{data.get('source')} — "
                        f"{data.get('available_mw')} MW "
                        f"@ {data.get('cost_coeff')}"
                    )

            elif performative == 'AGREE':
                if ACCRA_DR_JID in sender:
                    print(
                        f"[ECG DISPATCH] 🤝 DR AGREE: "
                        f"target {data.get('target_mw')} MW acknowledged"
                    )

            elif performative == 'FAILURE':
                if ACCRA_DR_JID in sender:
                    self._handle_dr_failure(agent, beliefs, data, tick)

            elif performative == 'REFUSE':
                print(
                    f"[ECG DISPATCH] ❌ REFUSE from "
                    f"{data.get('source')}: {data.get('reason')}"
                )

        def _handle_inform(
            self,
            agent: ECGCentralDispatchAgent,
            beliefs: ECGCentralDispatchBeliefs,
            data: dict,
            sender: str,
            tick: int,
        ) -> None:
            if any(jid in sender for jid in DISTRICT_JIDS):
                district = data['district']
                updated_demands = {
                    **beliefs.district_demands,
                    district: data['demand_mw'],
                }
                beliefs.update(
                    'district_demands', updated_demands,
                    f"INFORM from {district}: {data['demand_mw']:.1f} MW",
                    tick,
                )

            elif GRIDCO_FAULT_JID in sender:
                faults = beliefs.active_faults.copy()
                fault_district = data['district']
                if fault_district not in faults:
                    faults.append(fault_district)
                beliefs.update(
                    'active_faults', faults,
                    f"FAULT: {data['fault_type']} in {fault_district}",
                    tick,
                )
                print(
                    f"[ECG DISPATCH] ⚠ FAULT ALERT: "
                    f"{data['fault_type']} — {fault_district}"
                )

            elif ECG_FORECAST_JID in sender:
                forecast = {
                    **beliefs.forecast,
                    data['district']: data['forecast_mw'],
                }
                beliefs.update(
                    'forecast', forecast,
                    f"Forecast for {data['district']}: "
                    f"{data['forecast_mw']:.1f} MW",
                    tick,
                )

            elif any(jid in sender for jid in RENEWABLE_JIDS):
                print(
                    f"[ECG DISPATCH] ✅ Injection confirmed: "
                    f"{data.get('injecting_mw')} MW from {sender}"
                )

            elif ACCRA_DR_JID in sender:
                beliefs.update(
                    'demand_response_active', False,
                    f"DR completed: {data.get('achieved_mw', 0)} MW shed",
                    tick,
                )
                agent.dr_execution_pending = False
                print(
                    f"[ECG DISPATCH] ✅ DR SUCCESS result: "
                    f"{data.get('achieved_mw')} MW shed"
                )

        def _handle_dr_failure(
            self,
            agent: ECGCentralDispatchAgent,
            beliefs: ECGCentralDispatchBeliefs,
            data: dict,
            tick: int,
        ) -> None:
            gap_mw = data.get('gap_mw', 0)
            shed_so_far = 0.0
            for district in SHEDDING_ORDER:
                if shed_so_far >= gap_mw:
                    break
                agent.env.district_status[district] = 'shedding'
                shed_so_far += DISTRICT_CAPACITY[district] * 0.3
                beliefs.audit_log.append({
                    'tick': tick,
                    'event': 'DUMSOR_ROTATION',
                    'district': district,
                    'reason': 'DR_SHORTFALL',
                    'reason_chain': (
                        f"demand_high → CNP_insufficient → "
                        f"DR_shortfall → shed_{district}"
                    ),
                })
                print(
                    f"[ECG DISPATCH] 🔴 DUMSOR ROTATION: "
                    f"{district} — reason: DR shortfall {gap_mw:.1f} MW"
                )

            beliefs.update(
                'demand_response_active', False,
                f"DR failed, load shedding executed for {gap_mw:.1f} MW gap",
                tick,
            )
            agent.dr_execution_pending = False

    # ── Behaviour 3: Periodic broadcast to all districts ─────────

    class BroadcastBehaviour(PeriodicBehaviour):
        """Sends system-wide status updates to all five district zone agents."""

        async def run(self) -> None:
            agent: ECGCentralDispatchAgent = self.agent  # type: ignore[assignment]
            env = agent.env
            sender_jid = str(agent.jid)

            payload = {
                'status': agent.current_desire,
                'system_utilisation': env.get_utilisation_pct(),
                'active_intention': agent.current_intention,
                'active_desire': agent.current_desire,
            }

            for district_jid in DISTRICT_JIDS:
                msg = build_message(
                    to_jid=district_jid,
                    performative='INFORM',
                    payload=payload,
                    sender_jid=sender_jid,
                    tick=env.tick,
                )
                await self.send(msg)

            print(
                f"[ECG DISPATCH] 📡 BROADCAST tick {env.tick} — "
                f"desire={agent.current_desire}, "
                f"intention={agent.current_intention}, "
                f"utilisation={env.get_utilisation_pct():.1%}"
            )

    # ── Behaviour 4: Execute the active intention/plan ──────────

    class ExecuteIntentionBehaviour(CyclicBehaviour):
        """Runs the plan selected by the current intention."""

        async def run(self) -> None:
            agent: ECGCentralDispatchAgent = self.agent  # type: ignore[assignment]
            intention = agent.current_intention
            tick = agent.env.tick

            if intention in ('initiate_contract_net', 'emergency_contract_net'):
                if not agent.beliefs.pending_cnp_id:
                    demand = agent.beliefs.get_total_demand()
                    capacity = agent.beliefs.total_managed_capacity_mw
                    request_mw = max(0.0, demand - capacity * 0.90)
                    if request_mw > 0:
                        result = await initiate_contract_net(
                            agent, request_mw, tick,
                        )
                        awarded = result.get('awarded_mw', 0.0)
                        if not result['success'] or awarded < request_mw:
                            gap = request_mw - awarded
                            print(
                                f"[ECG DISPATCH] CNP gap: {gap:.1f} MW "
                                f"— escalating to Demand Response"
                            )
                            agent.beliefs.update(
                                'demand_response_active', True,
                                f"CNP insufficient, gap={gap:.1f}MW",
                                tick,
                            )
                    agent.beliefs.pending_cnp_id = None

            elif intention == 'optimise_renewable_mix':
                if not agent.beliefs.pending_cnp_id:
                    await initiate_contract_net(agent, 30.0, tick)
                    agent.beliefs.pending_cnp_id = None

            if agent.beliefs.demand_response_active and not agent.dr_execution_pending:
                demand = agent.beliefs.get_total_demand()
                capacity = agent.beliefs.total_managed_capacity_mw
                gap_mw = max(0, demand - capacity * 0.90)
                if gap_mw > 0:
                    dr_msg = build_message(
                        to_jid=ACCRA_DR_JID,
                        performative='REQUEST',
                        payload={
                            'target_reduction_mw': gap_mw,
                            'priority': (
                                'high'
                                if agent.current_desire == 'EMERGENCY_STABILISE'
                                else 'normal'
                            ),
                            'tick': tick,
                        },
                        sender_jid=str(agent.jid),
                        tick=tick,
                    )
                    await self.send(dr_msg)
                    agent.dr_execution_pending = True
                    print(
                        f"[ECG DISPATCH] 🏭 DR REQUEST: {gap_mw:.1f} MW "
                        f"to accra_industrial_dr"
                    )

            interval = DEMO_TICK_INTERVAL if agent.demo_mode else TICK_INTERVAL
            await asyncio.sleep(interval)

    # ── Agent setup ──────────────────────────────────────────────

    async def setup(self) -> None:
        bdi_loop = self.BDILoopBehaviour()
        self.add_behaviour(bdi_loop)

        receive_belief = self.ReceiveAndUpdateBelief()
        self.add_behaviour(receive_belief)

        execute_intention = self.ExecuteIntentionBehaviour()
        self.add_behaviour(execute_intention)

        tick = DEMO_TICK_INTERVAL if self.demo_mode else TICK_INTERVAL
        broadcast_period = BROADCAST_INTERVAL * tick
        broadcast = self.BroadcastBehaviour(period=broadcast_period)
        self.add_behaviour(broadcast)

        print(
            "[ECG DISPATCH] ═══════════════════════════════════════\n"
            "[ECG DISPATCH]  ECG Central Dispatch Agent ONLINE\n"
            "[ECG DISPATCH]  BDI Architecture Active\n"
            f"[ECG DISPATCH]  Managed capacity: "
            f"{self.beliefs.total_managed_capacity_mw} MW\n"
            "[ECG DISPATCH] ═══════════════════════════════════════"
        )
