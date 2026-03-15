"""
Shared pytest fixtures for the GridMind test suite.

All fixtures produce plain Python objects — no SPADE agents,
no XMPP server required.
"""
from __future__ import annotations

import random

import pytest

from gridmind.bdi.belief_base import ECGCentralDispatchBeliefs
from gridmind.environment.ghana_grid_state import GhanaGridEnvironment


@pytest.fixture()
def fresh_env() -> GhanaGridEnvironment:
    """A fresh GhanaGridEnvironment with base demands loaded."""
    return GhanaGridEnvironment()


@pytest.fixture()
def fresh_beliefs() -> ECGCentralDispatchBeliefs:
    """A fresh ECGCentralDispatchBeliefs with default values."""
    return ECGCentralDispatchBeliefs()


@pytest.fixture()
def seeded_random():
    """Seed the global RNG for reproducible DR compliance draws."""
    random.seed(42)
    yield
    random.seed()
