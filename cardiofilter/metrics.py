"""Signal-quality and detection-accuracy metrics.

Signal quality is measured against a clean reference (available in the controlled
noise experiments because noise is added synthetically). Detection accuracy follows
the convention of the PhysioNet/CinC segmentation literature: a detected event is a
true positive when it lies within a tolerance window of an unmatched reference event
(Springer et al., 2016 used 100 ms).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_TOLERANCE_S = 0.1
"""Matching tolerance between a detected and an annotated event, in seconds."""


def _pair(reference: np.ndarray, test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    reference = np.asarray(reference, dtype=np.float64)
    test = np.asarray(test, dtype=np.float64)
    if reference.shape != test.shape:
        raise ValueError("reference and test must have the same shape")
    if reference.size == 0:
        raise ValueError("signals must not be empty")
    return reference, test


def snr_db(reference: np.ndarray, test: np.ndarray) -> float:
    """Signal-to-noise ratio of ``test`` relative to the clean ``reference`` (dB)."""
    reference, test = _pair(reference, test)
    signal_power = float(np.sum(reference**2))
    error_power = float(np.sum((test - reference) ** 2))
    if signal_power == 0.0:
        raise ValueError("reference has zero power")
    if error_power == 0.0:
        return float("inf")
    return 10.0 * np.log10(signal_power / error_power)


def snr_improvement_db(reference: np.ndarray, noisy: np.ndarray, filtered: np.ndarray) -> float:
    """``SNR(filtered) - SNR(noisy)`` in dB; positive means the filter helped."""
    return snr_db(reference, filtered) - snr_db(reference, noisy)


def prd(reference: np.ndarray, test: np.ndarray) -> float:
    """Percent root-mean-square difference (lower is better)."""
    reference, test = _pair(reference, test)
    denom = float(np.sum(reference**2))
    if denom == 0.0:
        raise ValueError("reference has zero power")
    return 100.0 * float(np.sqrt(np.sum((test - reference) ** 2) / denom))


def correlation(reference: np.ndarray, test: np.ndarray) -> float:
    """Pearson correlation coefficient between the two signals."""
    reference, test = _pair(reference, test)
    ref_c = reference - reference.mean()
    test_c = test - test.mean()
    denom = float(np.sqrt(np.sum(ref_c**2) * np.sum(test_c**2)))
    if denom == 0.0:
        return 0.0
    return float(np.sum(ref_c * test_c) / denom)


@dataclass(frozen=True)
class DetectionScore:
    """Event-detection accuracy for one label (e.g. S1)."""

    true_positives: int
    false_positives: int
    false_negatives: int
    mean_abs_error_s: float
    """Mean |t_detected - t_reference| over matched pairs (NaN when none matched)."""

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def match_events(
    reference: np.ndarray, detected: np.ndarray, tolerance_s: float = DEFAULT_TOLERANCE_S
) -> list[tuple[int, int]]:
    """Greedy one-to-one matching of detected to reference events by time proximity.

    Pairs are formed in order of increasing absolute time difference; each event is used
    at most once. Returns ``(reference_index, detected_index)`` pairs.
    """
    reference = np.asarray(reference, dtype=np.float64)
    detected = np.asarray(detected, dtype=np.float64)
    if tolerance_s < 0:
        raise ValueError("tolerance_s must be non-negative")
    if reference.size == 0 or detected.size == 0:
        return []
    diffs = np.abs(reference[:, None] - detected[None, :])
    candidates = np.argwhere(diffs <= tolerance_s)
    order = np.argsort(diffs[candidates[:, 0], candidates[:, 1]], kind="stable")
    used_ref: set[int] = set()
    used_det: set[int] = set()
    pairs: list[tuple[int, int]] = []
    for ref_i, det_i in candidates[order]:
        if ref_i in used_ref or det_i in used_det:
            continue
        used_ref.add(int(ref_i))
        used_det.add(int(det_i))
        pairs.append((int(ref_i), int(det_i)))
    return pairs


def score_detection(
    reference: np.ndarray, detected: np.ndarray, tolerance_s: float = DEFAULT_TOLERANCE_S
) -> DetectionScore:
    """Precision/recall style scoring of detected event times against references."""
    reference = np.asarray(reference, dtype=np.float64)
    detected = np.asarray(detected, dtype=np.float64)
    pairs = match_events(reference, detected, tolerance_s)
    tp = len(pairs)
    if tp:
        errors = [abs(reference[r] - detected[d]) for r, d in pairs]
        mae = float(np.mean(errors))
    else:
        mae = float("nan")
    return DetectionScore(
        true_positives=tp,
        false_positives=int(detected.size - tp),
        false_negatives=int(reference.size - tp),
        mean_abs_error_s=mae,
    )
