"""Discrete wavelet transform (DWT) denoising for phonocardiograms.

The signal is decomposed with :func:`pywt.wavedec`; each detail band is thresholded
and the signal is rebuilt with :func:`pywt.waverec`. Two threshold rules are offered:

- ``"universal"`` (VisuShrink, Donoho & Johnstone 1994): ``sigma * sqrt(2 ln N)``
  with ``sigma`` estimated from the median absolute deviation of the finest detail band.
- ``"bayes"`` (BayesShrink, Chang et al. 2000): a per-level threshold
  ``sigma^2 / sigma_x`` adapted to the band's own signal variance.

At 4 kHz a 5-level decomposition gives detail bands 1000–2000, 500–1000, 250–500,
125–250 and 62.5–125 Hz and an approximation band of 0–62.5 Hz, so S1/S2 energy sits
in the three coarsest bands and most sensor hiss in the two finest.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pywt

ThresholdRule = Literal["universal", "bayes"]
ThresholdMode = Literal["soft", "hard"]

MAD_TO_SIGMA = 1.0 / 0.6745
"""Scale that converts a median absolute deviation to a Gaussian sigma."""


@dataclass(frozen=True)
class WaveletConfig:
    """Parameters of the wavelet denoiser."""

    wavelet: str = "coif4"
    level: int | None = 5
    rule: ThresholdRule = "universal"
    mode: ThresholdMode = "soft"
    scale: float = 1.0
    """Multiplier applied to the computed threshold (``<1`` is gentler)."""

    def validate(self) -> None:
        if self.wavelet not in pywt.wavelist(kind="discrete"):
            raise ValueError(f"unknown discrete wavelet: {self.wavelet!r}")
        if self.level is not None and self.level < 1:
            raise ValueError("level must be >= 1 or None")
        if self.rule not in ("universal", "bayes"):
            raise ValueError(f"unknown threshold rule: {self.rule!r}")
        if self.mode not in ("soft", "hard"):
            raise ValueError(f"unknown threshold mode: {self.mode!r}")
        if self.scale <= 0:
            raise ValueError("scale must be positive")


def estimate_noise_sigma(finest_detail: np.ndarray) -> float:
    """Robust noise standard deviation from the finest wavelet detail band."""
    finest_detail = np.asarray(finest_detail, dtype=np.float64)
    if finest_detail.size == 0:
        return 0.0
    return float(np.median(np.abs(finest_detail - np.median(finest_detail))) * MAD_TO_SIGMA)


def universal_threshold(sigma: float, n: int) -> float:
    """VisuShrink threshold."""
    if n < 2:
        return 0.0
    return float(sigma * np.sqrt(2.0 * np.log(n)))


def bayes_threshold(detail: np.ndarray, sigma: float) -> float:
    """BayesShrink threshold for one detail band."""
    detail = np.asarray(detail, dtype=np.float64)
    if detail.size == 0:
        return 0.0
    signal_var = max(float(np.mean(detail**2)) - sigma**2, 0.0)
    if signal_var == 0.0:
        return float(np.max(np.abs(detail)))
    return float(sigma**2 / np.sqrt(signal_var))


def _resolve_level(n: int, wavelet: str, level: int | None) -> int:
    max_level = pywt.dwt_max_level(n, pywt.Wavelet(wavelet).dec_len)
    if max_level < 1:
        raise ValueError("signal too short for a wavelet decomposition")
    return max_level if level is None else min(level, max_level)


DEFAULT_WAVELET = WaveletConfig()


def wavelet_denoise(x: np.ndarray, config: WaveletConfig = DEFAULT_WAVELET) -> np.ndarray:
    """Denoise ``x`` by thresholding its DWT detail coefficients; returns a new array."""
    config.validate()
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError("x must be one-dimensional")
    level = _resolve_level(len(x), config.wavelet, config.level)
    coeffs = pywt.wavedec(x, config.wavelet, level=level)
    approx, details = coeffs[0], coeffs[1:]
    sigma = estimate_noise_sigma(details[-1])
    if sigma == 0.0:
        return x.copy()

    new_details = []
    for detail in details:
        if config.rule == "universal":
            threshold = universal_threshold(sigma, len(x))
        else:
            threshold = bayes_threshold(detail, sigma)
        new_details.append(pywt.threshold(detail, threshold * config.scale, mode=config.mode))

    rebuilt = pywt.waverec([approx, *new_details], config.wavelet)
    return rebuilt[: len(x)]
