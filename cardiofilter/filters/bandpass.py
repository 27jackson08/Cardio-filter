"""Zero-phase Butterworth bandpass filtering.

Heart sounds S1 and S2 carry most of their energy between roughly 20 and 150 Hz, with
murmurs and valve clicks reaching several hundred hertz. The default 25–400 Hz band
removes low-frequency motion/respiration artefacts and high-frequency ambient noise
while preserving murmur content; it is the band most often reported for PCG
pre-processing (e.g. Springer et al., 2016).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal as sps


@dataclass(frozen=True)
class BandpassConfig:
    """Parameters of the Butterworth bandpass."""

    low_hz: float = 25.0
    high_hz: float = 400.0
    order: int = 4

    def validate(self, fs: int) -> None:
        nyquist = fs / 2.0
        if self.low_hz <= 0:
            raise ValueError("low_hz must be positive")
        if self.high_hz <= self.low_hz:
            raise ValueError("high_hz must exceed low_hz")
        if self.high_hz >= nyquist:
            raise ValueError(f"high_hz must be below Nyquist ({nyquist:g} Hz)")
        if self.order < 1:
            raise ValueError("order must be >= 1")


DEFAULT_BANDPASS = BandpassConfig()


def design_bandpass(fs: int, config: BandpassConfig = DEFAULT_BANDPASS) -> np.ndarray:
    """Return second-order sections for the configured Butterworth bandpass."""
    config.validate(fs)
    return sps.butter(
        config.order, [config.low_hz, config.high_hz], btype="bandpass", fs=fs, output="sos"
    )


def bandpass(x: np.ndarray, fs: int, config: BandpassConfig = DEFAULT_BANDPASS) -> np.ndarray:
    """Apply the bandpass forwards and backwards (zero phase) and return a new array."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError("x must be one-dimensional")
    sos = design_bandpass(fs, config)
    min_len = 3 * (sos.shape[0] * 2 + 1)
    if len(x) <= min_len:
        raise ValueError(f"signal too short for filtering (need > {min_len} samples)")
    return sps.sosfiltfilt(sos, x)
