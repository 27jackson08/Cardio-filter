"""Mains-hum removal with a cascade of zero-phase IIR notches.

Mains interference (50 Hz in most of the world, 60 Hz in the Americas) and its
harmonics sit inside the heart-sound band, so neither a bandpass nor wavelet
thresholding removes it. A narrow notch at the fundamental and its first harmonics
does, at the cost of a sliver of the S1/S2 spectrum (about 1.7 Hz wide at Q = 30).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal as sps

MAINS_CANDIDATES_HZ = (50.0, 60.0)


@dataclass(frozen=True)
class NotchConfig:
    """Parameters of the hum notch cascade."""

    freq_hz: float | None = None
    """Mains fundamental; ``None`` picks 50 or 60 Hz from the signal's spectrum and
    applies the notch only when hum is actually present (see ``min_hum_ratio``)."""
    harmonics: int = 3
    """Number of notched tones, fundamental included."""
    q: float = 30.0
    """Quality factor of each notch (centre frequency / −3 dB bandwidth)."""
    min_hum_ratio: float = 0.3
    """In automatic mode, notch only if the ±0.5 Hz band around the mains frequency
    holds at least this fraction of the power within ±5 Hz. Clean CirCor recordings
    sit below 0.26; hum at 10 dB SNR or worse sits above 0.39."""

    def validate(self, fs: int) -> None:
        if self.freq_hz is not None and self.freq_hz <= 0:
            raise ValueError("freq_hz must be positive or None")
        if self.harmonics < 1:
            raise ValueError("harmonics must be >= 1")
        if self.q <= 0:
            raise ValueError("q must be positive")
        if self.freq_hz is not None and self.freq_hz >= fs / 2:
            raise ValueError("freq_hz must be below Nyquist")
        if not 0 <= self.min_hum_ratio <= 1:
            raise ValueError("min_hum_ratio must lie in [0, 1]")


@dataclass(frozen=True)
class MainsEstimate:
    """Most likely mains frequency and how tonal the signal is there."""

    freq_hz: float
    ratio: float
    """Power within ±0.5 Hz of ``freq_hz`` over power within ±5 Hz (1.0 = pure tone)."""


DEFAULT_NOTCH = NotchConfig()


def detect_mains(
    x: np.ndarray, fs: int, candidates: tuple[float, ...] = MAINS_CANDIDATES_HZ
) -> MainsEstimate:
    """Pick the candidate mains frequency with the most tonal power.

    The ratio of power within ±0.5 Hz of the candidate to power within ±5 Hz is
    compared; the candidate with the larger ratio wins. Ties go to the first candidate.
    """
    x = np.asarray(x, dtype=np.float64)
    if x.size < fs:
        raise ValueError("need at least one second of signal to estimate mains frequency")
    nperseg = min(x.size, 8 * fs)
    freqs, power = sps.welch(x, fs=fs, nperseg=nperseg)
    best, best_ratio = candidates[0], -1.0
    for candidate in candidates:
        narrow = power[np.abs(freqs - candidate) <= 0.5].sum()
        wide = power[np.abs(freqs - candidate) <= 5.0].sum()
        ratio = narrow / wide if wide > 0 else 0.0
        if ratio > best_ratio:
            best, best_ratio = candidate, ratio
    return MainsEstimate(freq_hz=float(best), ratio=float(best_ratio))


def estimate_mains_frequency(
    x: np.ndarray, fs: int, candidates: tuple[float, ...] = MAINS_CANDIDATES_HZ
) -> float:
    """Most likely mains frequency (Hz); see :func:`detect_mains`."""
    return detect_mains(x, fs, candidates).freq_hz


def design_notch(fs: int, config: NotchConfig = DEFAULT_NOTCH, freq_hz: float | None = None):
    """Second-order sections notching ``freq_hz`` and its harmonics below Nyquist."""
    config.validate(fs)
    fundamental = freq_hz if freq_hz is not None else config.freq_hz
    if fundamental is None:
        raise ValueError("a mains frequency is required")
    sections = []
    for k in range(1, config.harmonics + 1):
        tone = fundamental * k
        if tone >= fs / 2:
            break
        b, a = sps.iirnotch(tone, config.q, fs=fs)
        sections.append(sps.tf2sos(b, a))
    return np.vstack(sections)


def notch(x: np.ndarray, fs: int, config: NotchConfig = DEFAULT_NOTCH) -> np.ndarray:
    """Remove mains hum and harmonics with zero-phase notches; returns a new array.

    With ``config.freq_hz`` unset the mains frequency is detected and the signal is
    returned unchanged (as a copy) when no hum is present, so clean recordings do not
    lose the sliver of heart-sound energy the notch would take.
    """
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError("x must be one-dimensional")
    config.validate(fs)
    if config.freq_hz is not None:
        freq = config.freq_hz
    else:
        estimate = detect_mains(x, fs)
        if estimate.ratio < config.min_hum_ratio:
            return x.copy()
        freq = estimate.freq_hz
    sos = design_notch(fs, config, freq)
    return sps.sosfiltfilt(sos, x)
