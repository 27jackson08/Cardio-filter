import numpy as np
import pytest

from cardiofilter.synth import generate_pcg


def test_generate_pcg_shape_and_scale():
    out = generate_pcg(duration=2.0, fs=4000, heart_rate=60.0)
    assert out.signal.shape == (8000,)
    assert out.fs == 4000
    assert out.duration == pytest.approx(2.0)
    assert np.max(np.abs(out.signal)) == pytest.approx(1.0)


def test_generate_pcg_event_times_follow_heart_rate():
    out = generate_pcg(duration=10.0, heart_rate=60.0, systole_fraction=0.3)
    assert np.allclose(np.diff(out.s1_times), 1.0)
    assert np.allclose(out.s2_times - out.s1_times[: len(out.s2_times)], 0.3)
    assert len(out.s2_times) <= len(out.s1_times)


def test_generate_pcg_energy_is_concentrated_at_events():
    out = generate_pcg(duration=4.0, heart_rate=60.0)
    t = np.arange(len(out.signal)) / out.fs
    near_event = np.zeros_like(t, dtype=bool)
    for c in np.concatenate([out.s1_times, out.s2_times]):
        near_event |= np.abs(t - c) < 0.06
    energy_in = np.sum(out.signal[near_event] ** 2)
    energy_out = np.sum(out.signal[~near_event] ** 2)
    assert energy_in > 100 * energy_out


def test_generate_pcg_jitter_is_reproducible():
    a = generate_pcg(duration=5.0, jitter=0.02, seed=7)
    b = generate_pcg(duration=5.0, jitter=0.02, seed=7)
    c = generate_pcg(duration=5.0, jitter=0.02, seed=8)
    assert np.array_equal(a.s1_times, b.s1_times)
    assert not np.array_equal(a.s1_times, c.s1_times)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"duration": 0},
        {"fs": 0},
        {"systole_fraction": 1.0},
        {"heart_rate": 0},
    ],
)
def test_generate_pcg_rejects_bad_arguments(kwargs):
    with pytest.raises(ValueError):
        generate_pcg(**kwargs)
