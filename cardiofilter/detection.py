"""S1/S2 detection from an envelope by peak picking and interval logic.

Pipeline:

1. Bandpass the recording (25–400 Hz by default).
2. Compute the normalised Shannon-energy envelope (sharp, good for peak picking) and a
   homomorphic envelope (smooth, good for estimating the cardiac period).
3. Estimate the cardiac period from the autocorrelation of the homomorphic envelope
   and derive a minimum peak spacing from it.
4. Pick Shannon-envelope peaks above a prominence threshold.
5. Label peaks as S1 or S2 using the physiological rule that systole (S1→S2) is
   shorter than diastole (S2→S1); conflicts are resolved by enforcing alternation.

The default parameters were tuned on a 12-subject development subset of CirCor
(44 recordings); see ``docs/results.md``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal as sps

from cardiofilter.envelope import Envelope, homomorphic_envelope, shannon_energy_envelope
from cardiofilter.filters.bandpass import DEFAULT_BANDPASS, BandpassConfig, bandpass

MIN_HEART_RATE_BPM = 40.0
MAX_HEART_RATE_BPM = 220.0
FALLBACK_PERIOD_S = 60.0 / 75.0
"""Cardiac period assumed when the autocorrelation shows no usable peak."""


@dataclass(frozen=True)
class DetectionConfig:
    """Tunable parameters of the detector."""

    bandpass: BandpassConfig = DEFAULT_BANDPASS
    prominence: float = 0.2
    """Minimum peak prominence in units of envelope standard deviations."""
    min_spacing_fraction: float = 0.3
    """Minimum peak spacing as a fraction of the estimated cardiac period."""
    min_spacing_s: float = 0.12
    """Absolute floor on the peak spacing (seconds), guarding against a wrong period."""
    period_dominance: float = 0.7
    """An autocorrelation peak counts as the period if it reaches this fraction of the
    tallest candidate; the shortest such lag wins, which avoids locking onto two cycles."""
    apply_bandpass: bool = True


DEFAULT_DETECTION = DetectionConfig()


@dataclass(frozen=True)
class Detection:
    """Result of :func:`detect_heart_sounds`."""

    s1_times: np.ndarray
    s2_times: np.ndarray
    peak_times: np.ndarray
    envelope: Envelope
    heart_rate_bpm: float


def estimate_cardiac_period(envelope: Envelope, dominance: float = 0.7) -> float:
    """Cardiac period (s) from the envelope autocorrelation.

    Candidate lags are restricted to the physiological heart-rate range. Among the
    autocorrelation peaks in that range, the shortest lag whose height is at least
    ``dominance`` times the tallest is returned, so that a two-cycle lag does not win
    merely because it is marginally taller.
    """
    if not 0 < dominance <= 1:
        raise ValueError("dominance must lie in (0, 1]")
    values = envelope.values - np.mean(envelope.values)
    if values.size < 4 or np.all(values == 0):
        return FALLBACK_PERIOD_S
    acf = sps.correlate(values, values, mode="full")[values.size - 1 :]
    acf = acf / acf[0]
    lag_min = int(np.floor(envelope.fs * 60.0 / MAX_HEART_RATE_BPM))
    lag_max = min(int(np.ceil(envelope.fs * 60.0 / MIN_HEART_RATE_BPM)), acf.size - 1)
    if lag_max <= lag_min:
        return FALLBACK_PERIOD_S
    segment = acf[lag_min : lag_max + 1]
    peaks, _ = sps.find_peaks(segment)
    if peaks.size == 0:
        return FALLBACK_PERIOD_S
    heights = segment[peaks]
    candidates = peaks[heights >= dominance * heights.max()]
    return float((lag_min + candidates[0]) / envelope.fs)


def label_s1_s2(peak_times: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split sorted peak times into S1 and S2 using the systole < diastole rule.

    Each peak votes S1 when the gap to the next peak is shorter than the gap from the
    previous one. The vote sequence is then forced to alternate by choosing the
    starting label that agrees with the most votes.
    """
    peak_times = np.asarray(peak_times, dtype=np.float64)
    n = peak_times.size
    if n == 0:
        return np.zeros(0), np.zeros(0)
    if n == 1:
        return peak_times.copy(), np.zeros(0)
    gaps = np.diff(peak_times)
    prev_gap = np.concatenate([[np.inf], gaps])
    next_gap = np.concatenate([gaps, [np.inf]])
    votes_s1 = next_gap < prev_gap
    parity = np.arange(n) % 2 == 0
    agreement_even = np.sum(votes_s1 == parity)
    agreement_odd = np.sum(votes_s1 == ~parity)
    is_s1 = parity if agreement_even >= agreement_odd else ~parity
    return peak_times[is_s1], peak_times[~is_s1]


def pick_peaks(
    envelope: Envelope, period_s: float, config: DetectionConfig = DEFAULT_DETECTION
) -> np.ndarray:
    """Indices of envelope peaks that are prominent and physiologically spaced."""
    spacing_s = max(config.min_spacing_s, config.min_spacing_fraction * period_s)
    distance = max(int(round(spacing_s * envelope.fs)), 1)
    peaks, _ = sps.find_peaks(envelope.values, prominence=config.prominence, distance=distance)
    return peaks


def detect_heart_sounds(
    x: np.ndarray, fs: int, config: DetectionConfig = DEFAULT_DETECTION
) -> Detection:
    """Locate S1 and S2 in a PCG recording."""
    x = np.asarray(x, dtype=np.float64)
    filtered = bandpass(x, fs, config.bandpass) if config.apply_bandpass else x
    envelope = shannon_energy_envelope(filtered, fs)
    period = estimate_cardiac_period(homomorphic_envelope(filtered, fs), config.period_dominance)
    peaks = pick_peaks(envelope, period, config)
    peak_times = envelope.times[peaks]
    s1, s2 = label_s1_s2(peak_times)
    return Detection(
        s1_times=s1,
        s2_times=s2,
        peak_times=peak_times,
        envelope=envelope,
        heart_rate_bpm=60.0 / period,
    )
