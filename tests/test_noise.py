import numpy as np
import pytest
from scipy import signal as sps

from cardiofilter.noise import NOISE_TYPES, make_noise, mix_at_snr

FS = 4000
N = 4 * FS


def _band_fraction(x: np.ndarray, low: float, high: float) -> float:
    f, p = sps.welch(x, fs=FS, nperseg=2048)
    mask = (f >= low) & (f <= high)
    return float(np.sum(p[mask]) / np.sum(p))


@pytest.mark.parametrize("kind", sorted(NOISE_TYPES))
def test_noise_is_unit_variance_and_reproducible(kind):
    a = make_noise(kind, N, FS, np.random.default_rng(3))
    b = make_noise(kind, N, FS, np.random.default_rng(3))
    assert a.shape == (N,)
    assert np.std(a) == pytest.approx(1.0, rel=1e-6)
    assert abs(np.mean(a)) < 1e-9
    assert np.array_equal(a, b)


def test_noise_spectral_shapes():
    rng = np.random.default_rng(0)
    assert _band_fraction(make_noise("rumble", N, FS, rng), 0, 25) > 0.95
    assert _band_fraction(make_noise("ambient", N, FS, rng), 250, 1600) > 0.90
    assert _band_fraction(make_noise("hum", N, FS, rng), 45, 155) > 0.98
    pink = make_noise("pink", N, FS, rng)
    assert _band_fraction(pink, 0, 100) > _band_fraction(pink, 1000, 1100) * 5
    white = make_noise("white", N, FS, rng)
    assert _band_fraction(white, 0, 1000) == pytest.approx(0.5, abs=0.05)


def test_make_noise_errors():
    with pytest.raises(ValueError, match="unknown noise type"):
        make_noise("thunder", N, FS, np.random.default_rng(0))
    with pytest.raises(ValueError):
        make_noise("white", 1, FS, np.random.default_rng(0))


def test_mix_at_snr_hits_target():
    rng = np.random.default_rng(0)
    clean = np.sin(2 * np.pi * 50 * np.arange(N) / FS)
    noise = make_noise("white", N, FS, rng)
    for snr in (-5.0, 0.0, 10.0):
        noisy = mix_at_snr(clean, noise, snr)
        achieved = 10 * np.log10(np.mean(clean**2) / np.mean((noisy - clean) ** 2))
        assert achieved == pytest.approx(snr, abs=1e-9)


def test_mix_at_snr_errors():
    with pytest.raises(ValueError):
        mix_at_snr(np.ones(10), np.ones(5), 0.0)
    with pytest.raises(ValueError):
        mix_at_snr(np.zeros(10), np.ones(10), 0.0)
    with pytest.raises(ValueError):
        mix_at_snr(np.ones(10), np.zeros(10), 0.0)
