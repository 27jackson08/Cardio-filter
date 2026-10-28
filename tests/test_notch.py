import numpy as np
import pytest

from cardiofilter.filters import (
    FILTER_METHODS,
    NotchConfig,
    apply_method,
    bandpass,
    estimate_mains_frequency,
    notch,
)
from cardiofilter.filters.notch import design_notch
from cardiofilter.metrics import snr_db
from cardiofilter.noise import make_noise, mix_at_snr
from cardiofilter.synth import generate_pcg

FS = 4000


def _rms(x):
    return float(np.sqrt(np.mean(x**2)))


def test_notch_removes_hum_and_keeps_heart_band(rng):
    # S1 at 40 Hz and S2 at 80 Hz, so neither sits exactly on the 50 Hz notch.
    pcg = generate_pcg(duration=10.0, s1_freq=40.0, s2_freq=80.0, seed=0)
    hum = make_noise("hum", len(pcg.signal), pcg.fs, rng)
    noisy = mix_at_snr(pcg.signal, hum, -5.0)
    cleaned = notch(noisy, pcg.fs, NotchConfig(freq_hz=50.0))
    assert snr_db(pcg.signal, cleaned) > snr_db(pcg.signal, noisy) + 15.0
    assert _rms(cleaned - pcg.signal) < 0.2 * _rms(pcg.signal)


def test_notch_auto_detects_50_or_60_hz(pcg, rng):
    t = np.arange(len(pcg.signal)) / pcg.fs
    for mains in (50.0, 60.0):
        hum = np.sin(2 * np.pi * mains * t) + 0.3 * np.sin(2 * np.pi * 2 * mains * t)
        noisy = mix_at_snr(pcg.signal, hum, 0.0)
        assert estimate_mains_frequency(noisy, pcg.fs) == mains
        cleaned = notch(noisy, pcg.fs)  # freq_hz=None -> auto
        assert snr_db(pcg.signal, cleaned) > snr_db(pcg.signal, noisy) + 10.0


def test_notch_is_zero_phase_and_narrow():
    t = np.arange(2 * FS) / FS
    tone_45 = np.sin(2 * np.pi * 45 * t)
    out = notch(tone_45, FS, NotchConfig(freq_hz=50.0, q=30.0))
    assert _rms(out) > 0.9 * _rms(tone_45)
    assert np.argmax(np.correlate(out[FS:], tone_45[FS:], mode="full")) == len(out[FS:]) - 1
    sos = design_notch(FS, NotchConfig(freq_hz=50.0, harmonics=100))
    assert sos.shape[0] == 39  # harmonics stop below Nyquist (2000 Hz)


@pytest.mark.parametrize(
    "cfg",
    [
        NotchConfig(freq_hz=0.0),
        NotchConfig(freq_hz=3000.0),
        NotchConfig(harmonics=0),
        NotchConfig(q=0.0),
    ],
)
def test_notch_config_validation(cfg):
    with pytest.raises(ValueError):
        notch(np.zeros(FS * 2), FS, cfg)


def test_notch_input_validation():
    with pytest.raises(ValueError):
        notch(np.zeros((10, 2)), FS)
    with pytest.raises(ValueError):
        estimate_mains_frequency(np.zeros(100), FS)
    with pytest.raises(ValueError):
        design_notch(FS, NotchConfig())


def test_new_pipeline_methods_registered(pcg, rng):
    for name in ("bandpass+wavelet_bayes", "notch+bandpass", "notch+bandpass+wavelet_bayes"):
        assert name in FILTER_METHODS
    hum = make_noise("hum", len(pcg.signal), pcg.fs, rng)
    noisy = mix_at_snr(pcg.signal, hum, 0.0)
    plain = bandpass(noisy, pcg.fs)
    notched = apply_method("notch+bandpass", noisy, pcg.fs)
    assert snr_db(pcg.signal, notched) > snr_db(pcg.signal, plain) + 10.0
    combo = apply_method("notch+bandpass+wavelet_bayes", noisy, pcg.fs)
    assert combo.shape == noisy.shape and np.isfinite(combo).all()
