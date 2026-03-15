"""
FIPA-ACL message construction for the GridMind multi-agent system.

Every inter-agent message in GridMind is built through build_message()
so that performative, ontology, and conversation tracking are uniform.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from spade.message import Message


ONTOLOGY = 'gridmind-ecg-gridco-v1'
LANGUAGE = 'fipa-sl'


def build_message(
    to_jid: str,
    performative: str,
    payload: dict[str, Any],
    sender_jid: str,
    tick: int,
    conversation_id: str | None = None,
) -> Message:
    """Construct a FIPA-ACL compliant SPADE message.

    Parameters
    ----------
    to_jid:
        Recipient JID (use the constants from config.py).
    performative:
        FIPA performative — INFORM, CFP, PROPOSE, ACCEPT-PROPOSAL,
        REJECT-PROPOSAL, REQUEST, AGREE, FAILURE, etc.
    payload:
        Domain-specific key/value pairs merged into the body JSON.
    sender_jid:
        The sending agent's JID (included in body for traceability).
    tick:
        Current simulation tick at time of send.
    conversation_id:
        Optional thread identifier.  A uuid4 is generated when *None*.
    """
    msg = Message(to=to_jid)
    msg.set_metadata('performative', performative)
    msg.set_metadata('ontology', ONTOLOGY)
    msg.set_metadata('language', LANGUAGE)
    msg.set_metadata('conversation-id', conversation_id or str(uuid.uuid4()))
    msg.body = json.dumps({'sender': sender_jid, 'tick': tick, **payload})
    return msg


def parse_message(msg: Message) -> dict[str, Any]:
    """Deserialise a SPADE message body back into a Python dict."""
    return json.loads(msg.body)
