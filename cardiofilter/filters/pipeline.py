"""Named filtering methods compared in the experiments."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from cardiofilter.filters.bandpass import BandpassConfig, bandpass
from cardiofilter.filters.wavelet import WaveletConfig, wavelet_denoise

FilterFn = Callable[[np.ndarray, int], np.ndarray]


def _none(x: np.ndarray, fs: int) -> np.ndarray:
    return np.asarray(x, dtype=np.float64).copy()


def _bandpass(x: np.ndarray, fs: int) -> np.ndarray:
    return bandpass(x, fs, BandpassConfig())


def _wavelet(x: np.ndarray, fs: int) -> np.ndarray:
    return wavelet_denoise(x, WaveletConfig())


def _wavelet_bayes(x: np.ndarray, fs: int) -> np.ndarray:
    return wavelet_denoise(x, WaveletConfig(rule="bayes"))


def _bandpass_wavelet(x: np.ndarray, fs: int) -> np.ndarray:
    return wavelet_denoise(bandpass(x, fs, BandpassConfig()), WaveletConfig())


FILTER_METHODS: dict[str, FilterFn] = {
    "none": _none,
    "bandpass": _bandpass,
    "wavelet": _wavelet,
    "wavelet_bayes": _wavelet_bayes,
    "bandpass+wavelet": _bandpass_wavelet,
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
