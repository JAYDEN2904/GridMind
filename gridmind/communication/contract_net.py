"""
Contract Net Protocol orchestration for ECG Central Dispatch.

Implements the full FIPA Contract Net Protocol: CFP broadcast to all
renewable sources, proposal collection with deadline, scoring by
available_mw / cost_coeff, ACCEPT-PROPOSAL to winner, REJECT-PROPOSAL
to losers.  Every round is uniquely identified by a conversation_id
and fully audit-logged.
"""
from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from gridmind.communication.message_factory import build_message
from gridmind.config import (
    RENEWABLE_CONFIG,
    KALEO_SOLAR_JID,
    NZEMA_SOLAR_JID,
    KETA_WIND_JID,
    XMPP_SERVER,
    CNP_DEADLINE_TICKS,
    TICK_INTERVAL,
    DEMO_TICK_INTERVAL,
)


async def initiate_contract_net(
    agent: Any,
    request_mw: float,
    tick: int,
    behaviour: Any = None,
) -> dict[str, Any]:
    """Execute a full FIPA Contract Net Protocol round.

    Parameters
    ----------
    agent:
        The ECGCentralDispatchAgent instance (must have .beliefs, .jid,
        .demo_mode, and a send() coroutine available via behaviours).
    request_mw:
        The MW shortfall that needs to be procured from renewables.
    tick:
        Current simulation tick.

    Returns
    -------
    dict with keys: success, awarded_mw, winner, proposals
    """
    conversation_id = f"cnp-ecg-{tick}-{str(uuid4())[:8]}"
    agent.beliefs.update(
        'pending_cnp_id',
        conversation_id,
        f"Contract Net initiated for {request_mw:.1f} MW",
        tick,
    )
    agent.beliefs.update(
        'pending_cnp_proposals',
        [],
        'Reset CNP proposals for new round',
        tick,
    )

    sender_jid = str(agent.jid)
    renewable_jids = [KALEO_SOLAR_JID, NZEMA_SOLAR_JID, KETA_WIND_JID]

    for jid in renewable_jids:
        cfp_msg = build_message(
            to_jid=jid,
            performative='CFP',
            payload={
                'request_mw': round(request_mw, 2),
                'deadline_ticks': CNP_DEADLINE_TICKS,
                'conversation_id': conversation_id,
            },
            sender_jid=sender_jid,
            tick=tick,
            conversation_id=conversation_id,
        )
        await behaviour.send(cfp_msg)

    print(
        f"[ECG DISPATCH] 📢 CFP sent to all renewables "
        f"— need {request_mw:.1f} MW (conv: {conversation_id})"
    )

    tick_interval = DEMO_TICK_INTERVAL if agent.demo_mode else TICK_INTERVAL
    await asyncio.sleep(CNP_DEADLINE_TICKS * tick_interval)

    proposals = agent.beliefs.pending_cnp_proposals

    if not proposals:
        print(
            "[ECG DISPATCH] ⚠ No proposals received "
            "— all renewables offline"
        )
        agent.beliefs.audit_log.append({
            'tick': tick,
            'agent': 'ecg_central_dispatch',
            'event': 'CNP_NO_PROPOSALS',
            'conversation_id': conversation_id,
            'request_mw': request_mw,
            'reason_chain': 'No renewable proposals received for CFP',
        })
        return {
            'success': False,
            'awarded_mw': 0.0,
            'winner': None,
            'proposals': [],
        }

    def score(proposal: dict) -> float:
        return proposal['available_mw'] / proposal['cost_coeff']

    ranked = sorted(proposals, key=score, reverse=True)
    winner = ranked[0]
    losers = ranked[1:]

    print(
        f"[ECG DISPATCH] 🏆 CNP WINNER: {winner['source']} "
        f"— {winner['available_mw']:.1f} MW @ {winner['cost_coeff']}"
    )

    awarded_mw = min(request_mw, winner['available_mw'])
    winner_jid = RENEWABLE_CONFIG[winner['source']]['jid']

    accept_msg = build_message(
        to_jid=winner_jid,
        performative='ACCEPT-PROPOSAL',
        payload={
            'conversation_id': conversation_id,
            'accepted_mw': round(awarded_mw, 2),
            'winner': winner['source'],
        },
        sender_jid=sender_jid,
        tick=tick,
        conversation_id=conversation_id,
    )
    await behaviour.send(accept_msg)

    for loser in losers:
        loser_jid = RENEWABLE_CONFIG[loser['source']]['jid']
        reject_msg = build_message(
            to_jid=loser_jid,
            performative='REJECT-PROPOSAL',
            payload={
                'conversation_id': conversation_id,
                'source': loser['source'],
            },
            sender_jid=sender_jid,
            tick=tick,
            conversation_id=conversation_id,
        )
        await behaviour.send(reject_msg)

    agent.beliefs.audit_log.append({
        'tick': tick,
        'agent': 'ecg_central_dispatch',
        'event': 'CNP_COMPLETE',
        'conversation_id': conversation_id,
        'winner': winner['source'],
        'awarded_mw': awarded_mw,
        'proposals_received': len(proposals),
        'reason_chain': (
            f"CNP round {conversation_id}: {len(proposals)} proposals, "
            f"winner={winner['source']} with {awarded_mw:.1f} MW "
            f"(score={score(winner):.1f})"
        ),
    })

    return {
        'success': True,
        'awarded_mw': awarded_mw,
        'winner': winner['source'],
        'proposals': proposals,
    }
