import math

import numpy as np
import pytest

from cardiofilter.metrics import (
    DetectionScore,
    correlation,
    match_events,
    prd,
    score_detection,
    snr_db,
    snr_improvement_db,
)


def test_snr_db_known_values():
    ref = np.ones(100)
    assert snr_db(ref, ref) == math.inf
    noisy = ref + 0.1
    assert snr_db(ref, noisy) == pytest.approx(20.0)
    assert snr_improvement_db(ref, noisy, ref + 0.01) == pytest.approx(20.0)


def test_prd_and_correlation():
    ref = np.sin(np.linspace(0, 10, 500))
    assert prd(ref, ref) == 0.0
    assert prd(ref, ref * 1.1) == pytest.approx(10.0)
    assert correlation(ref, ref) == pytest.approx(1.0)
    assert correlation(ref, -ref) == pytest.approx(-1.0)
    assert correlation(ref, np.zeros_like(ref)) == 0.0


def test_metric_input_validation():
    with pytest.raises(ValueError):
        snr_db(np.ones(3), np.ones(4))
    with pytest.raises(ValueError):
        snr_db(np.array([]), np.array([]))
    with pytest.raises(ValueError):
        snr_db(np.zeros(3), np.ones(3))
    with pytest.raises(ValueError):
        prd(np.zeros(3), np.ones(3))


def test_match_events_is_one_to_one_and_prefers_closest():
    ref = np.array([1.0, 2.0, 3.0])
    det = np.array([1.04, 1.06, 2.5, 3.01])
    pairs = match_events(ref, det, tolerance_s=0.1)
    assert sorted(pairs) == [(0, 0), (2, 3)]
    assert match_events(ref, np.array([]), 0.1) == []
    assert match_events(np.array([]), det, 0.1) == []
    with pytest.raises(ValueError):
        match_events(ref, det, tolerance_s=-1)


def test_score_detection_counts():
    ref = np.array([1.0, 2.0, 3.0, 4.0])
    det = np.array([1.02, 2.5, 2.98, 3.97, 5.0])
    score = score_detection(ref, det, tolerance_s=0.1)
    assert (score.true_positives, score.false_positives, score.false_negatives) == (3, 2, 1)
    assert score.precision == pytest.approx(3 / 5)
    assert score.recall == pytest.approx(3 / 4)
    assert score.f1 == pytest.approx(2 * 0.6 * 0.75 / 1.35)
    assert score.mean_abs_error_s == pytest.approx((0.02 + 0.02 + 0.03) / 3)


def test_score_detection_empty_cases():
    none = score_detection(np.array([1.0]), np.array([]))
    assert none.recall == 0.0 and none.precision == 0.0 and none.f1 == 0.0
    assert math.isnan(none.mean_abs_error_s)
    assert DetectionScore(0, 0, 0, float("nan")).f1 == 0.0
