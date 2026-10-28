"""CardioFilter: heart-sound signal processing for a low-cost digital stethoscope.

The package is organised by processing stage:

- :mod:`cardiofilter.synth`     – synthetic phonocardiogram (PCG) generator used for tests
- :mod:`cardiofilter.io`        – WAV loading and CirCor segmentation annotations
- :mod:`cardiofilter.filters`   – Butterworth bandpass and wavelet denoising
- :mod:`cardiofilter.noise`     – controlled noise models and SNR-calibrated mixing
- :mod:`cardiofilter.envelope`  – Shannon-energy and homomorphic envelopes
- :mod:`cardiofilter.detection` – S1/S2 peak detection and labelling
- :mod:`cardiofilter.metrics`   – signal-quality and detection-accuracy metrics
- :mod:`cardiofilter.visualize` – waveform, spectrogram and envelope plots
- :mod:`cardiofilter.experiments` – controlled-noise experiment runner
"""

from cardiofilter.version import __version__

__all__ = ["__version__"]
