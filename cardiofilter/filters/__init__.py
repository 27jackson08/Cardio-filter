"""Filtering methods compared in CardioFilter."""

from cardiofilter.filters.bandpass import DEFAULT_BANDPASS, BandpassConfig, bandpass
from cardiofilter.filters.pipeline import FILTER_METHODS, apply_method
from cardiofilter.filters.wavelet import DEFAULT_WAVELET, WaveletConfig, wavelet_denoise

__all__ = [
    "DEFAULT_BANDPASS",
    "DEFAULT_WAVELET",
    "FILTER_METHODS",
    "BandpassConfig",
    "WaveletConfig",
    "apply_method",
    "bandpass",
    "wavelet_denoise",
]
