"""Shared fixtures for the CardioFilter test-suite."""

from __future__ import annotations

import numpy as np
import pytest

from cardiofilter.synth import SyntheticPCG, generate_pcg


@pytest.fixture(scope="session")
def pcg() -> SyntheticPCG:
    """A 10 s clean synthetic PCG at 4 kHz, 75 bpm."""
    return generate_pcg(duration=10.0, fs=4000, heart_rate=75.0, seed=0)


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(1234)
