import numpy as np
import pytest

from cardiofilter.envelope import (
    Envelope,
    homomorphic_envelope,
    normalize,
    shannon_energy,
    shannon_energy_envelope,
)


def test_normalize():
    x = np.array([1.0, 2.0, 3.0])
    y = normalize(x)
    assert np.mean(y) == pytest.approx(0.0)
    assert np.std(y) == pytest.approx(1.0)
    assert np.array_equal(normalize(np.ones(4)), np.zeros(4))


def test_shannon_energy_properties():
    assert np.array_equal(shannon_energy(np.zeros(5)), np.zeros(5))
    e = shannon_energy(np.array([0.0, 0.5, 1.0, -0.5]))
    assert e[0] == pytest.approx(0.0, abs=1e-9)
    assert e[1] == pytest.approx(e[3])
    assert e[1] > e[2] >= 0.0  # medium amplitudes are emphasised over the peak


def test_shannon_envelope_peaks_align_with_events(pcg):
    env = shannon_energy_envelope(pcg.signal, pcg.fs)
    assert env.fs == pytest.approx(100.0)
    assert env.values.shape == env.times.shape
    assert np.all(np.diff(env.times) > 0)
    for t in np.concatenate([pcg.s1_times, pcg.s2_times]):
        idx = np.argmin(np.abs(env.times - t))
        window = env.values[max(idx - 5, 0) : idx + 6]
        assert window.max() > 1.0


def test_shannon_envelope_without_smoothing_and_short_input(pcg):
    env = shannon_energy_envelope(pcg.signal, pcg.fs, smooth_s=0.0)
    assert env.values.size > 0
    with pytest.raises(ValueError):
        shannon_energy_envelope(np.zeros(10), 4000)


def test_homomorphic_envelope_tracks_events(pcg):
    env = homomorphic_envelope(pcg.signal, pcg.fs)
    assert env.fs == pytest.approx(100.0)
    for t in pcg.s1_times:
        idx = np.argmin(np.abs(env.times - t))
        assert env.values[max(idx - 3, 0) : idx + 4].max() > 0.5
    with pytest.raises(ValueError):
        homomorphic_envelope(np.zeros(10), 4000)
    with pytest.raises(ValueError):
        homomorphic_envelope(pcg.signal, pcg.fs, cutoff_hz=5000)


def test_envelope_shape_validation():
    with pytest.raises(ValueError):
        Envelope(values=np.zeros(3), times=np.zeros(2), fs=1.0)
