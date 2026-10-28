"""Controlled-noise experiments and dataset-level evaluation.

For every (recording, noise type, input SNR, method) combination a trial adds
synthetic noise to the recording, filters it, and measures:

- signal quality against the original recording (SNR, SNR improvement, PRD, correlation)
- S1/S2 detection accuracy against the CirCor annotations (precision, recall, F1)

The original recording is treated as the clean reference, which is the convention
in the PCG denoising literature. It means any alteration of the original counts
against a method, including removal of genuine out-of-band content, so the detection
scores are the complementary, annotation-based view.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, fields
from pathlib import Path

import numpy as np

from cardiofilter.detection import DEFAULT_DETECTION, DetectionConfig, detect_heart_sounds
from cardiofilter.filters import FILTER_METHODS, apply_method
from cardiofilter.io import LABEL_S1, LABEL_S2, Record, Segmentation
from cardiofilter.metrics import DEFAULT_TOLERANCE_S, correlation, prd, score_detection, snr_db
from cardiofilter.noise import NOISE_TYPES, make_noise, mix_at_snr
from cardiofilter.synth import generate_pcg

DEFAULT_NOISE_TYPES = tuple(sorted(NOISE_TYPES))
DEFAULT_SNR_LEVELS = (-5.0, 0.0, 5.0, 10.0, 15.0)
DEFAULT_METHODS = tuple(FILTER_METHODS)


@dataclass(frozen=True)
class ExperimentConfig:
    noise_types: tuple[str, ...] = DEFAULT_NOISE_TYPES
    snr_levels_db: tuple[float, ...] = DEFAULT_SNR_LEVELS
    methods: tuple[str, ...] = DEFAULT_METHODS
    tolerance_s: float = DEFAULT_TOLERANCE_S
    seed: int = 0
    max_duration_s: float | None = 30.0
    detection: DetectionConfig = DEFAULT_DETECTION

    def validate(self) -> None:
        unknown_noise = set(self.noise_types) - set(NOISE_TYPES)
        if unknown_noise:
            raise ValueError(f"unknown noise types: {sorted(unknown_noise)}")
        unknown_methods = set(self.methods) - set(FILTER_METHODS)
        if unknown_methods:
            raise ValueError(f"unknown methods: {sorted(unknown_methods)}")
        if not self.snr_levels_db:
            raise ValueError("snr_levels_db must not be empty")
        if self.max_duration_s is not None and self.max_duration_s <= 0:
            raise ValueError("max_duration_s must be positive or None")


DEFAULT_EXPERIMENT = ExperimentConfig()


@dataclass(frozen=True)
class TrialResult:
    record: str
    noise_type: str
    snr_in_db: float
    method: str
    snr_out_db: float
    snr_improvement_db: float
    prd_percent: float
    correlation: float
    s1_precision: float
    s1_recall: float
    s1_f1: float
    s2_precision: float
    s2_recall: float
    s2_f1: float
    s1_mae_s: float
    heart_rate_bpm: float


def _reference_events(segmentation: Segmentation) -> tuple[np.ndarray, np.ndarray]:
    return segmentation.s1_times, segmentation.s2_times


def _trim(record: Record, max_duration_s: float | None) -> Record:
    if max_duration_s is None or record.duration <= max_duration_s:
        return record
    n = int(max_duration_s * record.fs)
    seg = record.segmentation
    if seg is not None:
        keep = seg.ends <= max_duration_s
        seg = Segmentation(seg.starts[keep], seg.ends[keep], seg.labels[keep])
    return Record(signal=record.signal[:n], fs=record.fs, name=record.name, segmentation=seg)


def evaluate_detection(
    signal: np.ndarray,
    fs: int,
    segmentation: Segmentation,
    tolerance_s: float = DEFAULT_TOLERANCE_S,
    detection: DetectionConfig = DEFAULT_DETECTION,
) -> dict[str, float]:
    """Run the detector and score it against annotations inside annotated spans only."""
    det = detect_heart_sounds(signal, fs, detection)
    ref_s1, ref_s2 = _reference_events(segmentation)
    det_s1 = det.s1_times[segmentation.is_annotated(det.s1_times)]
    det_s2 = det.s2_times[segmentation.is_annotated(det.s2_times)]
    s1 = score_detection(ref_s1, det_s1, tolerance_s)
    s2 = score_detection(ref_s2, det_s2, tolerance_s)
    return {
        "s1_precision": s1.precision,
        "s1_recall": s1.recall,
        "s1_f1": s1.f1,
        "s2_precision": s2.precision,
        "s2_recall": s2.recall,
        "s2_f1": s2.f1,
        "s1_mae_s": s1.mean_abs_error_s,
        "heart_rate_bpm": det.heart_rate_bpm,
    }


def run_trial(
    record: Record,
    noise_type: str,
    snr_in_db: float,
    method: str,
    rng: np.random.Generator,
    config: ExperimentConfig,
) -> TrialResult:
    """One noise-injection trial on an annotated record."""
    if record.segmentation is None:
        raise ValueError(f"record {record.name} has no segmentation annotations")
    clean = record.signal
    noise = make_noise(noise_type, len(clean), record.fs, rng)
    noisy = mix_at_snr(clean, noise, snr_in_db)
    filtered = apply_method(method, noisy, record.fs)
    scores = evaluate_detection(
        filtered, record.fs, record.segmentation, config.tolerance_s, config.detection
    )
    snr_out = snr_db(clean, filtered)
    return TrialResult(
        record=record.name,
        noise_type=noise_type,
        snr_in_db=snr_in_db,
        method=method,
        snr_out_db=snr_out,
        snr_improvement_db=snr_out - snr_db(clean, noisy),
        prd_percent=prd(clean, filtered),
        correlation=correlation(clean, filtered),
        **scores,
    )


def run_experiment(
    records: Iterable[Record], config: ExperimentConfig = DEFAULT_EXPERIMENT
) -> list[TrialResult]:
    """Run the full noise × SNR × method grid over annotated ``records``."""
    config.validate()
    rng = np.random.default_rng(config.seed)
    results: list[TrialResult] = []
    for record in records:
        if record.segmentation is None or len(record.segmentation) == 0:
            continue
        trimmed = _trim(record, config.max_duration_s)
        for noise_type in config.noise_types:
            for snr in config.snr_levels_db:
                # Same noise realisation for every method so methods are comparable.
                trial_seed = int(rng.integers(0, 2**32 - 1))
                for method in config.methods:
                    trial_rng = np.random.default_rng(trial_seed)
                    results.append(run_trial(trimmed, noise_type, snr, method, trial_rng, config))
    return results


def evaluate_dataset(
    records: Iterable[Record], config: ExperimentConfig = DEFAULT_EXPERIMENT
) -> list[dict[str, object]]:
    """Detection accuracy of every method on the recordings *as recorded* (no added noise)."""
    config.validate()
    rows: list[dict[str, object]] = []
    for record in records:
        if record.segmentation is None or len(record.segmentation) == 0:
            continue
        trimmed = _trim(record, config.max_duration_s)
        for method in config.methods:
            filtered = apply_method(method, trimmed.signal, trimmed.fs)
            scores = evaluate_detection(
                filtered, trimmed.fs, trimmed.segmentation, config.tolerance_s, config.detection
            )
            rows.append({"record": trimmed.name, "method": method, **scores})
    return rows


def synthetic_records(n: int, seed: int = 0, duration_s: float = 10.0) -> list[Record]:
    """Annotated synthetic records for running the pipeline without the dataset."""
    if n < 1:
        raise ValueError("n must be >= 1")
    rng = np.random.default_rng(seed)
    records = []
    for i in range(n):
        hr = float(rng.uniform(60.0, 140.0))
        pcg = generate_pcg(
            duration=duration_s, heart_rate=hr, jitter=0.01, seed=int(rng.integers(0, 1_000_000))
        )
        starts = np.concatenate([pcg.s1_times - 0.025, pcg.s2_times - 0.02])
        ends = np.concatenate([pcg.s1_times + 0.025, pcg.s2_times + 0.02])
        labels = np.concatenate(
            [np.full(len(pcg.s1_times), LABEL_S1), np.full(len(pcg.s2_times), LABEL_S2)]
        )
        order = np.argsort(starts)
        seg = Segmentation(starts[order], ends[order], labels[order])
        records.append(
            Record(signal=pcg.signal, fs=pcg.fs, name=f"synthetic_{i:03d}", segmentation=seg)
        )
    return records


def results_to_rows(results: Sequence[TrialResult]) -> list[dict[str, object]]:
    return [asdict(r) for r in results]


def write_csv(rows: Sequence[dict[str, object]], path: str | Path) -> Path:
    """Write dict rows to CSV; returns the path."""
    path = Path(path)
    if not rows:
        raise ValueError("no rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def summarize(
    rows: Sequence[dict[str, object]],
    by: Sequence[str],
    metrics: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    """Mean of every numeric metric grouped by the ``by`` keys (NaNs ignored)."""
    if not rows:
        return []
    if metrics is None:
        metrics = [k for k, v in rows[0].items() if k not in by and isinstance(v, (int, float))]
    groups: dict[tuple, list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault(tuple(row[k] for k in by), []).append(row)
    summary = []
    for key, members in sorted(groups.items(), key=lambda kv: tuple(str(k) for k in kv[0])):
        entry: dict[str, object] = dict(zip(by, key, strict=True))
        entry["n"] = len(members)
        for metric in metrics:
            values = np.array([float(m[metric]) for m in members])
            entry[metric] = float(np.nanmean(values)) if np.any(~np.isnan(values)) else float("nan")
        summary.append(entry)
    return summary


def markdown_table(
    rows: Sequence[dict[str, object]], columns: Sequence[str], digits: int = 2
) -> str:
    """Render rows as a GitHub-flavoured Markdown table."""
    if not rows:
        return "_no data_"
    header = "| " + " | ".join(columns) + " |"
    rule = "|" + "|".join(" --- " for _ in columns) + "|"
    lines = [header, rule]
    for row in rows:
        cells = []
        for col in columns:
            value = row.get(col, "")
            cells.append(f"{value:.{digits}f}" if isinstance(value, float) else str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def trial_fields() -> list[str]:
    return [f.name for f in fields(TrialResult)]
