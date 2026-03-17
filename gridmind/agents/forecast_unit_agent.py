"""
ECGForecastUnitAgent — demand forecasting agent for Ghana's national grid.

Collects demand history from the five district zone agents and computes
weighted moving average (WMA) forecasts.  When a district's forecast exceeds
the preemptive threshold, the agent sends an INFORM warning to ECG Central
Dispatch so the BDI loop can escalate to PREEMPTIVE_RESPONSE.

Two separate behaviours enforce the spec constraint: history collection
and forecast computation must never be merged into a single behaviour.
"""
from __future__ import annotations

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour

from gridmind.communication.message_factory import build_message, parse_message
from gridmind.config import (
    DISTRICT_CONFIG,
    DISTRICT_CAPACITY,
    ECG_DISPATCH_JID,
    TICK_INTERVAL,
    DEMO_TICK_INTERVAL,
    FORECAST_HORIZON,
    FORECAST_HISTORY_LEN,
    PREEMPTIVE_THRESHOLD_PCT,
)
from gridmind.environment.ghana_grid_state import GhanaGridEnvironment

_WEIGHTS: list[float] = [i + 1 for i in range(FORECAST_HISTORY_LEN)]
_WEIGHT_SUM: float = sum(_WEIGHTS)
WEIGHTS: list[float] = [w / _WEIGHT_SUM for w in _WEIGHTS]


class ECGForecastUnitAgent(Agent):
    """WMA demand-forecasting agent for ECG's five distribution districts."""

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

        self.beliefs: dict = {
            'demand_history': {
                district: [] for district in DISTRICT_CONFIG
            },
            'last_forecast': {},
            'forecast_errors': [],
        }

    class CollectHistoryBehaviour(CyclicBehaviour):
        """Receives INFORM messages from zone agents and buffers demand readings."""

        async def run(self) -> None:
            msg = await self.receive(timeout=1)
            if msg is None:
                return
            if msg.get_metadata('performative') != 'INFORM':
                return

            agent: ECGForecastUnitAgent = self.agent  # type: ignore[assignment]
            data = parse_message(msg)

            if 'district' not in data or 'demand_mw' not in data:
                return

            district = data['district']
            history = agent.beliefs['demand_history'].get(district)
            if history is None:
                return

            history.append(data['demand_mw'])
            if len(history) > FORECAST_HISTORY_LEN:
                history.pop(0)

    class ForecastAndAdviseBehaviour(PeriodicBehaviour):
        """Periodically computes WMA forecasts and warns dispatch of high utilisation."""

        async def run(self) -> None:
            agent: ECGForecastUnitAgent = self.agent  # type: ignore[assignment]

            for district in DISTRICT_CONFIG:
                history = agent.beliefs['demand_history'][district]
                if len(history) < 5:
                    continue

                w = WEIGHTS[-len(history):]
                w_sum = sum(w)
                w_normalised = [x / w_sum for x in w]
                forecast_mw = sum(
                    wi * ri for wi, ri in zip(w_normalised, history)
                )

                agent.beliefs['last_forecast'][district] = forecast_mw
                ceiling = DISTRICT_CAPACITY[district]
                utilisation = forecast_mw / ceiling

                confidence = min(
                    1.0, len(history) / FORECAST_HISTORY_LEN
                )

                if forecast_mw > ceiling * PREEMPTIVE_THRESHOLD_PCT:
                    forecast_msg = build_message(
                        to_jid=ECG_DISPATCH_JID,
                        performative='INFORM',
                        payload={
                            'district': district,
                            'forecast_mw': forecast_mw,
                            'ceiling_mw': ceiling,
                            'utilisation': utilisation,
                            'horizon_ticks': FORECAST_HORIZON,
                            'confidence': confidence,
                            'tick': agent.env.tick,
                        },
                        sender_jid=str(agent.jid),
                        tick=agent.env.tick,
                    )
                    await self.send(forecast_msg)
                    print(
                        f"[ECG FORECAST] 📈 WARNING: {district} forecast "
                        f"{forecast_mw:.1f} MW ({utilisation:.1%} of ceiling) "
                        f"in {FORECAST_HORIZON} ticks"
                    )
                else:
                    print(
                        f"[ECG FORECAST] {district}: {forecast_mw:.1f} MW "
                        f"forecast ({utilisation:.1%}) — normal"
                    )

    async def setup(self) -> None:
        collect = self.CollectHistoryBehaviour()
        self.add_behaviour(collect)

        tick = DEMO_TICK_INTERVAL if self.demo_mode else TICK_INTERVAL
        period = FORECAST_HORIZON * tick
        forecast = self.ForecastAndAdviseBehaviour(period=period)
        self.add_behaviour(forecast)

        print(
            f"[ECG FORECAST] Forecast Unit ONLINE — "
            f"horizon={FORECAST_HORIZON} ticks, "
            f"history_len={FORECAST_HISTORY_LEN}"
        )
