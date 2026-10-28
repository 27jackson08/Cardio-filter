import numpy as np
import pytest

from cardiofilter.detection import (
    DetectionConfig,
    detect_heart_sounds,
    estimate_cardiac_period,
    label_s1_s2,
)
from cardiofilter.envelope import Envelope, shannon_energy_envelope
from cardiofilter.metrics import score_detection
from cardiofilter.noise import make_noise, mix_at_snr
from cardiofilter.synth import generate_pcg


def test_detects_all_s1_s2_on_clean_signal(pcg):
    det = detect_heart_sounds(pcg.signal, pcg.fs)
    s1 = score_detection(pcg.s1_times, det.s1_times, tolerance_s=0.05)
    s2 = score_detection(pcg.s2_times, det.s2_times, tolerance_s=0.05)
    assert s1.f1 == 1.0 and s2.f1 == 1.0
    assert det.heart_rate_bpm == pytest.approx(75.0, abs=3.0)
    assert det.peak_times.size == det.s1_times.size + det.s2_times.size


@pytest.mark.parametrize("heart_rate", [55.0, 110.0, 150.0])
def test_detection_across_heart_rates(heart_rate):
    pcg = generate_pcg(duration=12.0, heart_rate=heart_rate, jitter=0.01, seed=1)
    det = detect_heart_sounds(pcg.signal, pcg.fs)
    assert score_detection(pcg.s1_times, det.s1_times, 0.05).f1 >= 0.95
    assert score_detection(pcg.s2_times, det.s2_times, 0.05).f1 >= 0.95
    assert det.heart_rate_bpm == pytest.approx(heart_rate, rel=0.08)


def test_detection_survives_moderate_noise(pcg, rng):
    noise = make_noise("white", len(pcg.signal), pcg.fs, rng)
    noisy = mix_at_snr(pcg.signal, noise, 5.0)
    det = detect_heart_sounds(noisy, pcg.fs)
    assert score_detection(pcg.s1_times, det.s1_times, 0.1).f1 >= 0.9


def test_detection_without_bandpass(pcg):
    det = detect_heart_sounds(pcg.signal, pcg.fs, DetectionConfig(apply_bandpass=False))
    assert score_detection(pcg.s1_times, det.s1_times, 0.05).f1 == 1.0


def test_label_s1_s2_rule_and_edge_cases():
    # systole 0.3 s, diastole 0.7 s, starting on S1
    peaks = np.array([0.0, 0.3, 1.0, 1.3, 2.0, 2.3])
    s1, s2 = label_s1_s2(peaks)
    assert np.allclose(s1, [0.0, 1.0, 2.0])
    assert np.allclose(s2, [0.3, 1.3, 2.3])
    # starting on S2
    s1, s2 = label_s1_s2(peaks[1:])
    assert np.allclose(s1, [1.0, 2.0])
    assert np.allclose(s2, [0.3, 1.3, 2.3])
    assert label_s1_s2(np.array([]))[0].size == 0
    s1, s2 = label_s1_s2(np.array([0.5]))
    assert s1.tolist() == [0.5] and s2.size == 0


def test_estimate_cardiac_period_fallbacks():
    flat = Envelope(values=np.zeros(200), times=np.arange(200) / 100, fs=100.0)
    assert estimate_cardiac_period(flat) == pytest.approx(0.8)
    tiny = Envelope(values=np.array([1.0, 2.0]), times=np.array([0.0, 0.01]), fs=100.0)
    assert estimate_cardiac_period(tiny) == pytest.approx(0.8)
    short = Envelope(
        values=np.random.default_rng(0).normal(size=20), times=np.arange(20) / 100, fs=100.0
    )
    assert estimate_cardiac_period(short) == pytest.approx(0.8)
    pcg = generate_pcg(duration=10.0, heart_rate=60.0)
    env = shannon_energy_envelope(pcg.signal, pcg.fs)
    assert estimate_cardiac_period(env) == pytest.approx(1.0, abs=0.03)
