"""Named filtering methods compared in the experiments."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from cardiofilter.filters.bandpass import DEFAULT_BANDPASS, bandpass
from cardiofilter.filters.notch import DEFAULT_NOTCH, notch
from cardiofilter.filters.wavelet import (
    DEFAULT_WAVELET,
    WaveletConfig,
    noise_sigma,
    wavelet_denoise,
)

FilterFn = Callable[[np.ndarray, int], np.ndarray]

BAYES = WaveletConfig(rule="bayes")


def _none(x: np.ndarray, fs: int) -> np.ndarray:
    return np.asarray(x, dtype=np.float64).copy()


def _bandpass(x: np.ndarray, fs: int) -> np.ndarray:
    return bandpass(x, fs, DEFAULT_BANDPASS)


def _wavelet(x: np.ndarray, fs: int) -> np.ndarray:
    return wavelet_denoise(x, DEFAULT_WAVELET)


def _wavelet_bayes(x: np.ndarray, fs: int) -> np.ndarray:
    return wavelet_denoise(x, BAYES)


def _bandpass_then_wavelet(x: np.ndarray, fs: int, config: WaveletConfig) -> np.ndarray:
    """Bandpass, then wavelet-threshold using the noise level of the *raw* signal.

    After a bandpass the finest wavelet band is empty, so estimating sigma from the
    filtered signal would make the wavelet stage a no-op.
    """
    sigma = noise_sigma(x, config)
    return wavelet_denoise(bandpass(x, fs, DEFAULT_BANDPASS), config, sigma=sigma)


def _bandpass_wavelet(x: np.ndarray, fs: int) -> np.ndarray:
    return _bandpass_then_wavelet(x, fs, DEFAULT_WAVELET)


def _bandpass_wavelet_bayes(x: np.ndarray, fs: int) -> np.ndarray:
    return _bandpass_then_wavelet(x, fs, BAYES)


def _notch_bandpass(x: np.ndarray, fs: int) -> np.ndarray:
    return bandpass(notch(x, fs, DEFAULT_NOTCH), fs, DEFAULT_BANDPASS)


def _notch_bandpass_wavelet_bayes(x: np.ndarray, fs: int) -> np.ndarray:
    return _bandpass_then_wavelet(notch(x, fs, DEFAULT_NOTCH), fs, BAYES)


FILTER_METHODS: dict[str, FilterFn] = {
    "none": _none,
    "bandpass": _bandpass,
    "wavelet": _wavelet,
    "wavelet_bayes": _wavelet_bayes,
    "bandpass+wavelet": _bandpass_wavelet,
    "bandpass+wavelet_bayes": _bandpass_wavelet_bayes,
    "notch+bandpass": _notch_bandpass,
    "notch+bandpass+wavelet_bayes": _notch_bandpass_wavelet_bayes,
}
"""Registry of method name -> ``f(x, fs) -> filtered``."""


def apply_method(name: str, x: np.ndarray, fs: int) -> np.ndarray:
    """Apply a registered filtering method by name."""
    try:
        fn = FILTER_METHODS[name]
    except KeyError as exc:
        known = ", ".join(sorted(FILTER_METHODS))
        raise ValueError(f"unknown filter method {name!r}; choose from: {known}") from exc
    return fn(x, fs)
