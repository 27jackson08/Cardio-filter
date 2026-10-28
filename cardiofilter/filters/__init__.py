"""Filtering methods compared in CardioFilter."""

from cardiofilter.filters.bandpass import DEFAULT_BANDPASS, BandpassConfig, bandpass
from cardiofilter.filters.notch import DEFAULT_NOTCH, NotchConfig, estimate_mains_frequency, notch
from cardiofilter.filters.pipeline import FILTER_METHODS, apply_method
from cardiofilter.filters.wavelet import (
    DEFAULT_WAVELET,
    WaveletConfig,
    noise_sigma,
    wavelet_denoise,
)

__all__ = [
    "DEFAULT_BANDPASS",
    "DEFAULT_NOTCH",
    "DEFAULT_WAVELET",
    "FILTER_METHODS",
    "BandpassConfig",
    "NotchConfig",
    "WaveletConfig",
    "apply_method",
    "bandpass",
    "estimate_mains_frequency",
    "notch",
    "noise_sigma",
    "wavelet_denoise",
]
