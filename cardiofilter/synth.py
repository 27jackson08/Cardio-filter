"""Synthetic phonocardiogram generator.

The generator produces a clean PCG with known S1/S2 timings so that filtering and
detection code can be tested deterministically without the real dataset. Each heart
sound is modelled as a Gaussian-windowed sinusoid, which is the standard
simplification used in the PCG literature (S1 ≈ 30–100 Hz, S2 ≈ 50–150 Hz).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_FS = 4000
"""Sampling rate of the CirCor DigiScope recordings (Hz)."""


@dataclass(frozen=True)
class SyntheticPCG:
    """A clean synthetic PCG together with its ground-truth event times."""

    signal: np.ndarray
    fs: int
    s1_times: np.ndarray
    s2_times: np.ndarray

    @property
    def duration(self) -> float:
        """Signal length in seconds."""
        return len(self.signal) / self.fs


def _gaussian_tone(
    t: np.ndarray, centre: float, freq: float, width: float, amplitude: float
) -> np.ndarray:
    """Return a sinusoid at ``freq`` under a Gaussian window centred on ``centre``."""
    window = np.exp(-0.5 * ((t - centre) / width) ** 2)
    return amplitude * window * np.sin(2.0 * np.pi * freq * (t - centre))


def generate_pcg(
    duration: float = 10.0,
    fs: int = DEFAULT_FS,
    heart_rate: float = 75.0,
    s1_freq: float = 50.0,
    s2_freq: float = 80.0,
    systole_fraction: float = 0.35,
    jitter: float = 0.0,
    seed: int | None = None,
) -> SyntheticPCG:
    """Generate a clean synthetic PCG with S1 and S2 at known times.

    Args:
        duration: Length of the signal in seconds.
        fs: Sampling rate in Hz.
        heart_rate: Beats per minute.
        s1_freq: Dominant frequency of S1 (Hz).
        s2_freq: Dominant frequency of S2 (Hz).
        systole_fraction: Fraction of the cardiac cycle between S1 and S2.
        jitter: Standard deviation (seconds) of random timing jitter per beat.
        seed: Seed for the jitter RNG.

    Returns:
        A :class:`SyntheticPCG` whose ``signal`` is scaled to a peak of 1.0.
    """
    if duration <= 0:
        raise ValueError("duration must be positive")
    if fs <= 0:
        raise ValueError("fs must be positive")
    if not 0 < systole_fraction < 1:
        raise ValueError("systole_fraction must lie in (0, 1)")
    if heart_rate <= 0:
        raise ValueError("heart_rate must be positive")

    rng = np.random.default_rng(seed)
    period = 60.0 / heart_rate
    n_samples = int(round(duration * fs))
    t = np.arange(n_samples) / fs

    beat_starts = np.arange(0.15, duration - 0.15, period)
    if jitter > 0:
        beat_starts = beat_starts + rng.normal(0.0, jitter, size=beat_starts.shape)
    s1_times = beat_starts
    s2_times = beat_starts + systole_fraction * period
    s2_times = s2_times[s2_times < duration - 0.05]

    signal = np.zeros(n_samples)
    for c in s1_times:
        signal = signal + _gaussian_tone(t, c, s1_freq, width=0.018, amplitude=1.0)
    for c in s2_times:
        signal = signal + _gaussian_tone(t, c, s2_freq, width=0.012, amplitude=0.7)

    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak
    return SyntheticPCG(signal=signal, fs=fs, s1_times=s1_times, s2_times=s2_times)
