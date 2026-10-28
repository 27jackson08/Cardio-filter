from pathlib import Path

import numpy as np
import pytest
from scipy.io import wavfile

from cardiofilter.io import (
    LABEL_DIASTOLE,
    LABEL_S1,
    LABEL_S2,
    LABEL_SYSTOLE,
    LABEL_UNANNOTATED,
    Segmentation,
    list_records,
    load_record,
    load_segmentation,
    load_wav,
    save_wav,
)


def _write_tsv(path: Path, rows) -> None:
    path.write_text("\n".join(f"{s:.4f}\t{e:.4f}\t{lab}" for s, e, lab in rows) + "\n")


@pytest.fixture
def circor_like(tmp_path: Path) -> Path:
    fs = 4000
    t = np.arange(fs * 2) / fs
    pcm = (0.5 * np.sin(2 * np.pi * 50 * t) * 32767).astype(np.int16)
    wavfile.write(tmp_path / "123_MV.wav", fs, pcm)
    rows = [
        (0.0, 0.2, LABEL_UNANNOTATED),
        (0.2, 0.3, LABEL_S1),
        (0.3, 0.6, LABEL_SYSTOLE),
        (0.6, 0.7, LABEL_S2),
        (0.7, 1.0, LABEL_DIASTOLE),
        (1.0, 1.1, LABEL_S1),
        (1.1, 1.4, LABEL_SYSTOLE),
        (1.4, 1.5, LABEL_S2),
        (1.5, 1.8, LABEL_DIASTOLE),
        (1.8, 2.0, LABEL_UNANNOTATED),
    ]
    _write_tsv(tmp_path / "123_MV.tsv", rows)
    wavfile.write(tmp_path / "123_AV.wav", fs, pcm)  # no annotations
    return tmp_path


def test_load_wav_scales_int16_to_unit_range(circor_like):
    signal, fs = load_wav(circor_like / "123_MV.wav")
    assert fs == 4000
    assert signal.dtype == np.float64
    assert np.max(np.abs(signal)) == pytest.approx(0.5, abs=1e-3)


def test_load_wav_averages_stereo_and_passes_float(tmp_path):
    stereo = np.stack([np.ones(100), -np.ones(100)], axis=1).astype(np.float32)
    wavfile.write(tmp_path / "s.wav", 1000, stereo)
    signal, fs = load_wav(tmp_path / "s.wav")
    assert fs == 1000
    assert np.allclose(signal, 0.0)


def test_load_wav_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_wav(tmp_path / "nope.wav")


def test_save_wav_roundtrip_clips(tmp_path):
    x = np.array([0.0, 0.5, 2.0, -2.0])
    out = save_wav(tmp_path / "o.wav", x, 4000)
    y, fs = load_wav(out)
    assert fs == 4000
    assert np.allclose(y, [0.0, 0.5, 1.0, -1.0], atol=1e-4)


def test_load_segmentation_parses_labels_and_event_times(circor_like):
    seg = load_segmentation(circor_like / "123_MV.tsv")
    assert len(seg) == 10
    assert np.allclose(seg.s1_times, [0.25, 1.05])
    assert np.allclose(seg.s2_times, [0.65, 1.45])
    assert seg.annotated_intervals() == [(0.2, 1.8)]
    assert seg.is_annotated(np.array([0.1, 0.5, 1.9])).tolist() == [False, True, False]


def test_load_segmentation_handles_gaps_and_empty(tmp_path):
    _write_tsv(tmp_path / "g.tsv", [(0, 1, 1), (1, 2, 2), (2, 3, 0), (3, 4, 3)])
    seg = load_segmentation(tmp_path / "g.tsv")
    assert seg.annotated_intervals() == [(0.0, 2.0), (3.0, 4.0)]
    (tmp_path / "e.tsv").write_text("")
    assert len(load_segmentation(tmp_path / "e.tsv")) == 0


def test_load_segmentation_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_segmentation(tmp_path / "missing.tsv")
    (tmp_path / "bad.tsv").write_text("0\t1\n")
    with pytest.raises(ValueError):
        load_segmentation(tmp_path / "bad.tsv")


def test_segmentation_validates_shapes():
    with pytest.raises(ValueError):
        Segmentation(np.zeros(2), np.zeros(3), np.zeros(2, dtype=int))
    with pytest.raises(ValueError):
        Segmentation(np.array([1.0]), np.array([0.5]), np.array([1]))


def test_load_record_with_and_without_tsv(circor_like):
    rec = load_record(circor_like / "123_MV.wav")
    assert rec.name == "123_MV"
    assert rec.segmentation is not None
    assert rec.duration == pytest.approx(2.0)
    rec2 = load_record(circor_like / "123_AV")
    assert rec2.segmentation is None


def test_list_records_filters_unannotated(circor_like):
    assert [p.name for p in list_records(circor_like)] == ["123_MV"]
    assert [p.name for p in list_records(circor_like, annotated_only=False)] == [
        "123_AV",
        "123_MV",
    ]
