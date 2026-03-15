"""
Tests for the Contract Net Protocol scoring and award logic.

Exercises the CNP formula (available_mw / cost_coeff) and award
computation in isolation — no SPADE messages, no async.
"""
from __future__ import annotations

from uuid import uuid4

import pytest


def _score(proposal: dict) -> float:
    """Reproduce the CNP scoring formula from contract_net.py."""
    return proposal['available_mw'] / proposal['cost_coeff']


PROPOSALS = [
    {'source': 'kaleo_solar', 'available_mw': 110.0, 'cost_coeff': 0.28},
    {'source': 'keta_wind', 'available_mw': 42.0, 'cost_coeff': 0.19},
    {'source': 'nzema_solar', 'available_mw': 18.0, 'cost_coeff': 0.31},
]


def test_cnp_scores_correctly():
    """kaleo_solar should win with score ~392.9 (110/0.28)."""
    ranked = sorted(PROPOSALS, key=_score, reverse=True)
    winner = ranked[0]

    assert winner['source'] == 'kaleo_solar', (
        f"Expected kaleo_solar to win, got {winner['source']}"
    )
    assert _score(winner) == pytest.approx(392.857, rel=1e-2), (
        f"Expected score ~392.9, got {_score(winner):.1f}"
    )

    keta_score = _score(ranked[1])
    assert keta_score == pytest.approx(221.053, rel=1e-2), (
        f"Expected keta score ~221.1, got {keta_score:.1f}"
    )

    nzema_score = _score(ranked[2])
    assert nzema_score == pytest.approx(58.065, rel=1e-2), (
        f"Expected nzema score ~58.1, got {nzema_score:.1f}"
    )


def test_cnp_awards_correct_mw():
    """Award should be min(request_mw, winner_available_mw)."""
    request_mw = 85.0
    winner_available = 110.0
    awarded = min(request_mw, winner_available)

    assert awarded == pytest.approx(85.0), (
        f"Expected awarded_mw=85.0, got {awarded}"
    )

    request_mw_large = 150.0
    awarded_large = min(request_mw_large, winner_available)
    assert awarded_large == pytest.approx(110.0), (
        f"Expected awarded_mw=110.0 when request exceeds capacity, "
        f"got {awarded_large}"
    )


def test_cnp_handles_no_proposals():
    """Empty proposals list should yield no winner and zero award."""
    proposals: list[dict] = []
    ranked = sorted(proposals, key=_score, reverse=True)

    assert len(ranked) == 0, "Expected empty ranked list"

    success = len(ranked) > 0
    awarded_mw = 0.0 if not success else min(85.0, ranked[0]['available_mw'])

    assert success is False, "Expected success=False with no proposals"
    assert awarded_mw == pytest.approx(0.0), (
        f"Expected awarded_mw=0.0, got {awarded_mw}"
    )


def test_cnp_conversation_id_uniqueness():
    """Each CNP round should produce a unique conversation ID."""
    tick = 42
    ids = [f"cnp-ecg-{tick}-{str(uuid4())[:8]}" for _ in range(10)]

    assert len(set(ids)) == 10, (
        f"Expected 10 unique conversation IDs, got {len(set(ids))}"
    )
