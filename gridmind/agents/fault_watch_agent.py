"""
GRIDCoFaultWatchAgent — purely reactive anomaly detector for Ghana's grid.

Receives INFORM messages from all five district zone agents, maintains a
rolling window of readings per district, and fires alerts to ECG Central
Dispatch when either a demand spike or a feeder loss is detected.  This
agent has NO goals, NO plans, NO deliberation — it is a textbook reactive
agent that maps percepts directly to actions via two threshold rules.
"""
from __future__ import annotations

import numpy as np
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour

from gridmind.config import (
    DISTRICT_CONFIG,
    GRIDCO_FAULT_JID,
    ECG_DISPATCH_JID,
    FAULT_WINDOW,
    FAULT_SIGMA_THRESHOLD,
)
from gridmind.communication.message_factory import build_message, parse_message
from gridmind.environment.ghana_grid_state import GhanaGridEnvironment


class GRIDCoFaultWatchAgent(Agent):
    """Reactive anomaly-detection agent modelling GRIDCo's fault monitoring."""

    def __init__(
        self,
        jid: str,
        password: str,
        env: GhanaGridEnvironment,
    ) -> None:
        super().__init__(jid, password)
        self.env = env
        self.rolling_windows: dict[str, list[float]] = {
            district_id: [] for district_id in DISTRICT_CONFIG
        }

    class FaultDetectionBehaviour(CyclicBehaviour):
        """Percept-driven rule engine: spike detection and feeder-loss detection."""

        async def run(self) -> None:
            msg = await self.receive(timeout=1)
            if msg is None:
                return

            agent: GRIDCoFaultWatchAgent = self.agent  # type: ignore[assignment]
            data = parse_message(msg)
            district = data.get('district')
            demand_mw = data.get('demand_mw')

            if district is None or demand_mw is None:
                return
            if district not in agent.rolling_windows:
                return

            window = agent.rolling_windows[district]
            window.append(float(demand_mw))
            if len(window) > FAULT_WINDOW:
                window.pop(0)

            if len(window) < 3:
                return

            mean = float(np.mean(window))
            std = float(np.std(window))
            sender_jid = str(agent.jid)

            if std >= 0.1 and demand_mw > mean + FAULT_SIGMA_THRESHOLD * std:
                severity = (demand_mw - mean) / std
                alert_payload = {
                    'district': district,
                    'fault_type': 'demand_spike',
                    'severity_sigma': round(severity, 4),
                    'demand_mw': demand_mw,
                    'tick': agent.env.tick,
                }
                alert_msg = build_message(
                    to_jid=ECG_DISPATCH_JID,
                    performative='INFORM',
                    payload=alert_payload,
                    sender_jid=sender_jid,
                    tick=agent.env.tick,
                )
                await self.send(alert_msg)
                agent.env.log_event(
                    agent='gridco_fault_watch',
                    event_type='demand_spike',
                    detail=f"{district} {severity:.2f}σ above normal "
                           f"({demand_mw:.1f} MW, mean={mean:.1f})",
                )
                print(
                    f"[GRIDCo FAULT WATCH] ⚠ SPIKE: {district} "
                    f"{severity:.2f}σ above normal"
                )

            if demand_mw < mean * 0.15 and mean > 50:
                loss_payload = {
                    'district': district,
                    'fault_type': 'feeder_loss',
                    'demand_mw': demand_mw,
                    'expected_mean': round(mean, 2),
                    'tick': agent.env.tick,
                }
                loss_msg = build_message(
                    to_jid=ECG_DISPATCH_JID,
                    performative='INFORM',
                    payload=loss_payload,
                    sender_jid=sender_jid,
                    tick=agent.env.tick,
                )
                await self.send(loss_msg)
                agent.env.log_event(
                    agent='gridco_fault_watch',
                    event_type='feeder_loss',
                    detail=f"{district} demand {demand_mw:.1f} MW, "
                           f"expected mean {mean:.1f} MW",
                )
                print(
                    f"[GRIDCo FAULT WATCH] 🔴 FEEDER LOSS: {district}"
                )

    async def setup(self) -> None:
        fault_detection = self.FaultDetectionBehaviour()
        self.add_behaviour(fault_detection)
        print("[GRIDCo FAULT WATCH] Agent started — monitoring all 5 districts")
