import numpy as np
import pytest
from scipy import signal as sps

from cardiofilter.filters import (
    FILTER_METHODS,
    BandpassConfig,
    WaveletConfig,
    apply_method,
    bandpass,
    wavelet_denoise,
)
from cardiofilter.filters.wavelet import (
    bayes_threshold,
    estimate_noise_sigma,
    universal_threshold,
)
from cardiofilter.metrics import snr_db
from cardiofilter.noise import make_noise, mix_at_snr

FS = 4000


def _tone(freq: float, seconds: float = 2.0) -> np.ndarray:
    t = np.arange(int(FS * seconds)) / FS
    return np.sin(2 * np.pi * freq * t)


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x**2)))


def test_bandpass_passes_band_and_rejects_out_of_band():
    cfg = BandpassConfig(low_hz=25, high_hz=400, order=4)
    assert _rms(bandpass(_tone(80), FS, cfg)) == pytest.approx(_rms(_tone(80)), rel=0.05)
    assert _rms(bandpass(_tone(5), FS, cfg)) < 0.05 * _rms(_tone(5))
    assert _rms(bandpass(_tone(1500), FS, cfg)) < 0.05 * _rms(_tone(1500))


def test_bandpass_is_zero_phase_and_does_not_mutate_input():
    x = _tone(80)
    original = x.copy()
    y = bandpass(x, FS)
    assert np.array_equal(x, original)
    lag = np.argmax(sps.correlate(y, x, mode="full")) - (len(x) - 1)
    assert lag == 0


@pytest.mark.parametrize(
    "cfg",
    [
        BandpassConfig(low_hz=0),
        BandpassConfig(low_hz=500, high_hz=400),
        BandpassConfig(high_hz=2000),
        BandpassConfig(order=0),
    ],
)
def test_bandpass_config_validation(cfg):
    with pytest.raises(ValueError):
        bandpass(_tone(80), FS, cfg)


def test_bandpass_rejects_bad_shapes():
    with pytest.raises(ValueError):
        bandpass(np.zeros((10, 2)), FS)
    with pytest.raises(ValueError):
        bandpass(np.zeros(5), FS)


def test_wavelet_denoise_improves_snr_of_noisy_pcg(pcg, rng):
    noise = make_noise("white", len(pcg.signal), pcg.fs, rng)
    noisy = mix_at_snr(pcg.signal, noise, 0.0)
    out = wavelet_denoise(noisy)
    assert out.shape == noisy.shape
    assert snr_db(pcg.signal, out) > snr_db(pcg.signal, noisy) + 3.0


@pytest.mark.parametrize("rule", ["universal", "bayes"])
@pytest.mark.parametrize("mode", ["soft", "hard"])
def test_wavelet_denoise_rules_and_modes_run(pcg, rng, rule, mode):
    noise = make_noise("white", len(pcg.signal), pcg.fs, rng)
    noisy = mix_at_snr(pcg.signal, noise, 5.0)
    out = wavelet_denoise(noisy, WaveletConfig(rule=rule, mode=mode))
    assert np.isfinite(out).all()
    assert snr_db(pcg.signal, out) > snr_db(pcg.signal, noisy)


def test_wavelet_denoise_odd_length_and_auto_level(pcg):
    x = pcg.signal[:4001]
    out = wavelet_denoise(x, WaveletConfig(level=None))
    assert out.shape == x.shape


def test_wavelet_denoise_returns_copy_when_noise_free():
    x = np.zeros(1024)
    out = wavelet_denoise(x)
    assert np.array_equal(out, x)
    assert out is not x


def test_wavelet_denoise_rejects_short_and_bad_shapes():
    with pytest.raises(ValueError):
        wavelet_denoise(np.zeros((8, 8)))
    with pytest.raises(ValueError):
        wavelet_denoise(np.zeros(4))


@pytest.mark.parametrize(
    "cfg",
    [
        WaveletConfig(wavelet="nope"),
        WaveletConfig(level=0),
        WaveletConfig(rule="magic"),
        WaveletConfig(mode="medium"),
        WaveletConfig(scale=0),
    ],
)
def test_wavelet_config_validation(cfg):
    with pytest.raises(ValueError):
        wavelet_denoise(np.zeros(1024), cfg)


def test_threshold_helpers():
    rng = np.random.default_rng(0)
    d = rng.normal(0, 2.0, 100_000)
    assert estimate_noise_sigma(d) == pytest.approx(2.0, rel=0.02)
    assert estimate_noise_sigma(np.array([])) == 0.0
    assert universal_threshold(1.0, 1) == 0.0
    assert universal_threshold(2.0, 1000) == pytest.approx(2.0 * np.sqrt(2 * np.log(1000)))
    assert bayes_threshold(np.array([]), 1.0) == 0.0
    # pure noise band -> threshold collapses to the max coefficient
    assert bayes_threshold(np.array([0.1, -0.2]), 10.0) == pytest.approx(0.2)
    assert 0 < bayes_threshold(d + 5.0 * np.sign(d), 2.0) < np.max(np.abs(d))


def test_filter_registry(pcg):
    assert set(FILTER_METHODS) == {
        "none",
        "bandpass",
        "wavelet",
        "wavelet_bayes",
        "bandpass+wavelet",
    }
    for name in FILTER_METHODS:
        out = apply_method(name, pcg.signal, pcg.fs)
        assert out.shape == pcg.signal.shape
    assert apply_method("none", pcg.signal, pcg.fs) is not pcg.signal
    with pytest.raises(ValueError, match="unknown filter method"):
        apply_method("fft-magic", pcg.signal, pcg.fs)
