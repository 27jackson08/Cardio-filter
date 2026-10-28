"""Controlled noise models used to stress the filtering methods.

Every generator returns a unit-variance array so that :func:`mix_at_snr` can scale it
to a target signal-to-noise ratio. The models cover the interference a low-cost
stethoscope actually meets:

- ``white``   – broadband sensor/ADC hiss
- ``pink``    – 1/f electronics and room noise
- ``hum``     – mains interference (50 Hz plus harmonics)
- ``rumble``  – sub-20 Hz motion and respiration artefacts (chest-piece movement)
- ``ambient`` – 300–1500 Hz band-limited noise approximating speech/room activity
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy import signal as sps

NoiseFn = Callable[[int, int, np.random.Generator], np.ndarray]


def _unit_variance(x: np.ndarray) -> np.ndarray:
    x = x - np.mean(x)
    std = np.std(x)
    return x / std if std > 0 else x


def white_noise(n: int, fs: int, rng: np.random.Generator) -> np.ndarray:
    return _unit_variance(rng.standard_normal(n))


def pink_noise(n: int, fs: int, rng: np.random.Generator) -> np.ndarray:
    """1/f noise shaped in the frequency domain."""
    spectrum = np.fft.rfft(rng.standard_normal(n))
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    weights = np.ones_like(freqs)
    weights[1:] = 1.0 / np.sqrt(freqs[1:])
    weights[0] = 0.0
    return _unit_variance(np.fft.irfft(spectrum * weights, n=n))


def mains_hum(
    n: int, fs: int, rng: np.random.Generator, freq: float = 50.0, harmonics: int = 3
) -> np.ndarray:
    """Mains hum with decaying harmonics and a random phase."""
    t = np.arange(n) / fs
    phase = rng.uniform(0.0, 2.0 * np.pi)
    hum = np.zeros(n)
    for k in range(1, harmonics + 1):
        hum = hum + np.sin(2.0 * np.pi * freq * k * t + k * phase) / k
    return _unit_variance(hum)


def band_limited_noise(
    n: int, fs: int, rng: np.random.Generator, low_hz: float, high_hz: float
) -> np.ndarray:
    """White noise restricted to ``[low_hz, high_hz]`` with a zero-phase Butterworth."""
    nyquist = fs / 2.0
    high = min(high_hz, 0.95 * nyquist)
    if low_hz <= 0:
        sos = sps.butter(4, high, btype="lowpass", fs=fs, output="sos")
    else:
        sos = sps.butter(4, [low_hz, high], btype="bandpass", fs=fs, output="sos")
    return _unit_variance(sps.sosfiltfilt(sos, rng.standard_normal(n)))


def rumble_noise(n: int, fs: int, rng: np.random.Generator) -> np.ndarray:
    return band_limited_noise(n, fs, rng, low_hz=0.0, high_hz=20.0)


def ambient_noise(n: int, fs: int, rng: np.random.Generator) -> np.ndarray:
    return band_limited_noise(n, fs, rng, low_hz=300.0, high_hz=1500.0)


NOISE_TYPES: dict[str, NoiseFn] = {
    "white": white_noise,
    "pink": pink_noise,
    "hum": mains_hum,
    "rumble": rumble_noise,
    "ambient": ambient_noise,
}


def make_noise(kind: str, n: int, fs: int, rng: np.random.Generator) -> np.ndarray:
    """Generate ``n`` samples of unit-variance noise of the given ``kind``."""
    try:
        fn = NOISE_TYPES[kind]
    except KeyError as exc:
        known = ", ".join(sorted(NOISE_TYPES))
        raise ValueError(f"unknown noise type {kind!r}; choose from: {known}") from exc
    if n < 2:
        raise ValueError("n must be >= 2")
    return fn(n, fs, rng)


def mix_at_snr(clean: np.ndarray, noise: np.ndarray, snr_db: float) -> np.ndarray:
    """Return ``clean + noise`` with the noise scaled to achieve ``snr_db``."""
    clean = np.asarray(clean, dtype=np.float64)
    noise = np.asarray(noise, dtype=np.float64)
    if clean.shape != noise.shape:
        raise ValueError("clean and noise must have the same shape")
    signal_power = float(np.mean(clean**2))
    noise_power = float(np.mean(noise**2))
    if signal_power == 0.0:
        raise ValueError("clean signal has zero power")
    if noise_power == 0.0:
        raise ValueError("noise has zero power")
    target_noise_power = signal_power / (10.0 ** (snr_db / 10.0))
    gain = np.sqrt(target_noise_power / noise_power)
    return clean + gain * noise
