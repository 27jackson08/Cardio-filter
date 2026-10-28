"""Envelope extraction for heart-sound localisation.

Two envelopes are provided:

- **Shannon energy** (Liang et al., 1997): ``-x^2 log(x^2)`` averaged over short
  windows. It emphasises medium-intensity components and suppresses both very low
  noise and very high spikes, which is why it is the standard front-end for S1/S2
  peak picking.
- **Homomorphic** envelope: the exponential of the low-passed log-magnitude
  (Gupta et al., 2007; also used by Springer's HSMM). Smoother, no window hop.

Both return an envelope sampled at a reduced ``env_fs`` plus matching time stamps.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal as sps

EPSILON = 1e-12


@dataclass(frozen=True)
class Envelope:
    """An envelope sampled at ``fs`` with time stamps ``times`` (seconds)."""

    values: np.ndarray
    times: np.ndarray
    fs: float

    def __post_init__(self) -> None:
        if self.values.shape != self.times.shape:
            raise ValueError("values and times must share a shape")


def normalize(x: np.ndarray) -> np.ndarray:
    """Zero-mean, unit-variance copy (returns zeros for a constant input)."""
    x = np.asarray(x, dtype=np.float64)
    std = np.std(x)
    if std == 0.0:
        return np.zeros_like(x)
    return (x - np.mean(x)) / std


def shannon_energy(x: np.ndarray) -> np.ndarray:
    """Sample-wise Shannon energy of a signal normalised to unit peak."""
    x = np.asarray(x, dtype=np.float64)
    peak = np.max(np.abs(x)) if x.size else 0.0
    if peak == 0.0:
        return np.zeros_like(x)
    x2 = (x / peak) ** 2
    return np.maximum(-x2 * np.log(x2 + EPSILON), 0.0)


def shannon_energy_envelope(
    x: np.ndarray,
    fs: int,
    window_s: float = 0.02,
    hop_s: float = 0.01,
    smooth_s: float = 0.03,
) -> Envelope:
    """Normalised average Shannon energy envelope.

    Args:
        x: Band-passed PCG.
        fs: Sampling rate (Hz).
        window_s: Averaging window length (seconds), 20 ms by convention.
        hop_s: Hop between windows (seconds), 10 ms by convention.
        smooth_s: Length of a final moving-average smoother (seconds); 0 disables it.
    """
    x = np.asarray(x, dtype=np.float64)
    window = max(int(round(window_s * fs)), 1)
    hop = max(int(round(hop_s * fs)), 1)
    if x.size < window:
        raise ValueError("signal shorter than the envelope window")
    energy = shannon_energy(x)
    n_frames = 1 + (len(energy) - window) // hop
    starts = np.arange(n_frames) * hop
    frames = np.lib.stride_tricks.sliding_window_view(energy, window)[starts]
    averaged = frames.mean(axis=1)
    env_fs = fs / hop
    if smooth_s > 0:
        k = max(int(round(smooth_s * env_fs)), 1)
        averaged = np.convolve(averaged, np.ones(k) / k, mode="same")
    times = (starts + window / 2.0) / fs
    return Envelope(values=normalize(averaged), times=times, fs=env_fs)


def homomorphic_envelope(
    x: np.ndarray, fs: int, cutoff_hz: float = 8.0, decimate_to_hz: float = 100.0
) -> Envelope:
    """Low-passed log-magnitude envelope, decimated to ``decimate_to_hz``."""
    x = np.asarray(x, dtype=np.float64)
    if x.size < 32:
        raise ValueError("signal too short for a homomorphic envelope")
    if not 0 < cutoff_hz < fs / 2:
        raise ValueError("cutoff_hz must lie in (0, fs/2)")
    sos = sps.butter(2, cutoff_hz, btype="lowpass", fs=fs, output="sos")
    log_mag = np.log(np.abs(x) + EPSILON)
    env = np.exp(sps.sosfiltfilt(sos, log_mag))
    step = max(int(round(fs / decimate_to_hz)), 1)
    env = env[::step]
    times = np.arange(len(env)) * step / fs
    return Envelope(values=normalize(env), times=times, fs=fs / step)
