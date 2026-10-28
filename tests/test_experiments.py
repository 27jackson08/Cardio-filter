import math

import numpy as np
import pytest

from cardiofilter import experiments as xp
from cardiofilter.io import Record, Segmentation


@pytest.fixture(scope="module")
def records():
    return xp.synthetic_records(2, seed=3, duration_s=6.0)


@pytest.fixture(scope="module")
def small_config():
    return xp.ExperimentConfig(
        noise_types=("white", "hum"),
        snr_levels_db=(0.0, 10.0),
        methods=("none", "bandpass", "bandpass+wavelet"),
        max_duration_s=5.0,
        seed=1,
    )


def test_synthetic_records_are_annotated(records):
    assert [r.name for r in records] == ["synthetic_000", "synthetic_001"]
    seg = records[0].segmentation
    assert seg is not None and len(seg) > 0
    assert np.all(np.diff(seg.starts) > 0)
    assert seg.s1_times.size >= 5 and seg.s2_times.size >= 5
    with pytest.raises(ValueError):
        xp.synthetic_records(0)


def test_run_experiment_grid_and_reproducibility(records, small_config):
    results = xp.run_experiment(records, small_config)
    assert len(results) == 2 * 2 * 2 * 3
    again = xp.run_experiment(records, small_config)
    assert [r.snr_out_db for r in results] == [r.snr_out_db for r in again]
    none_rows = [r for r in results if r.method == "none"]
    for r in none_rows:
        assert r.snr_out_db == pytest.approx(r.snr_in_db, abs=1e-6)
        assert r.snr_improvement_db == pytest.approx(0.0, abs=1e-6)
    bp = [r for r in results if r.method == "bandpass" and r.noise_type == "white"]
    assert all(r.snr_improvement_db > 3.0 for r in bp)
    assert all(0.0 <= r.s1_f1 <= 1.0 for r in results)


def test_run_experiment_trims_long_records(records):
    cfg = xp.ExperimentConfig(
        noise_types=("white",), snr_levels_db=(10.0,), methods=("none",), max_duration_s=2.0
    )
    results = xp.run_experiment(records, cfg)
    assert results and all(isinstance(r, xp.TrialResult) for r in results)
    trimmed = xp._trim(records[0], 2.0)
    assert trimmed.duration == pytest.approx(2.0)
    assert np.all(trimmed.segmentation.ends <= 2.0)
    assert xp._trim(records[0], None) is records[0]


def test_run_experiment_skips_unannotated_records(records, small_config):
    bare = Record(signal=records[0].signal, fs=records[0].fs, name="bare")
    empty = Record(
        signal=records[0].signal,
        fs=records[0].fs,
        name="empty",
        segmentation=Segmentation(np.zeros(0), np.zeros(0), np.zeros(0, dtype=int)),
    )
    assert xp.run_experiment([bare, empty], small_config) == []
    assert xp.evaluate_dataset([bare, empty], small_config) == []
    with pytest.raises(ValueError):
        xp.run_trial(bare, "white", 0.0, "none", np.random.default_rng(0), small_config)


def test_evaluate_dataset_scores_clean_synthetic_well(records, small_config):
    rows = xp.evaluate_dataset(records, small_config)
    assert len(rows) == 2 * 3
    assert all(r["s1_f1"] >= 0.9 for r in rows)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"noise_types": ("thunder",)},
        {"methods": ("fft",)},
        {"snr_levels_db": ()},
        {"max_duration_s": 0},
    ],
)
def test_config_validation(kwargs):
    with pytest.raises(ValueError):
        xp.ExperimentConfig(**kwargs).validate()


def test_summarize_csv_and_markdown(tmp_path, records, small_config):
    rows = xp.results_to_rows(xp.run_experiment(records, small_config))
    assert set(rows[0]) == set(xp.trial_fields())
    path = xp.write_csv(rows, tmp_path / "out" / "trials.csv")
    assert path.exists() and path.read_text().startswith("record,noise_type")
    by_method = xp.summarize(rows, by=["method"])
    assert [r["method"] for r in by_method] == ["bandpass", "bandpass+wavelet", "none"]
    assert all(r["n"] == 8 for r in by_method)
    none_row = next(r for r in by_method if r["method"] == "none")
    assert none_row["snr_improvement_db"] == pytest.approx(0.0, abs=1e-6)
    table = xp.markdown_table(by_method, ["method", "n", "s1_f1"])
    assert table.splitlines()[0] == "| method | n | s1_f1 |"
    assert len(table.splitlines()) == 2 + 3
    assert xp.markdown_table([], ["a"]) == "_no data_"
    assert xp.summarize([], by=["method"]) == []
    with pytest.raises(ValueError):
        xp.write_csv([], tmp_path / "empty.csv")


def test_summarize_ignores_nan():
    rows = [
        {"method": "a", "v": float("nan")},
        {"method": "a", "v": 2.0},
        {"method": "b", "v": float("nan")},
    ]
    out = xp.summarize(rows, by=["method"], metrics=["v"])
    assert out[0]["v"] == 2.0
    assert math.isnan(out[1]["v"])
