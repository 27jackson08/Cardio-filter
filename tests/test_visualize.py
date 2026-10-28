import matplotlib.pyplot as plt
import numpy as np
import pytest

from cardiofilter import visualize as viz
from cardiofilter.detection import detect_heart_sounds
from cardiofilter.io import Segmentation


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def test_plot_waveform_and_spectrogram(pcg, tmp_path):
    fig = viz.plot_waveform(
        {"raw": pcg.signal, "filtered": pcg.signal * 0.5}, pcg.fs, time_range=(0, 3)
    )
    assert len(fig.axes) == 2
    path = viz.save_figure(fig, str(tmp_path / "w.png"))
    assert (tmp_path / "w.png").stat().st_size > 1000
    fig2 = viz.plot_spectrogram(pcg.signal, pcg.fs)
    assert fig2.axes[0].get_ylabel() == "Frequency (Hz)"
    with pytest.raises(ValueError):
        viz.plot_waveform({}, pcg.fs)
    with pytest.raises(ValueError):
        viz.plot_spectrogram(np.zeros(10), pcg.fs)
    assert path.endswith("w.png")


def test_plot_detection_with_and_without_annotations(pcg):
    det = detect_heart_sounds(pcg.signal, pcg.fs)
    seg = Segmentation(
        pcg.s1_times - 0.02, pcg.s1_times + 0.02, np.ones(len(pcg.s1_times), dtype=int)
    )
    fig = viz.plot_detection(pcg.signal, pcg.fs, det, seg, time_range=(0, 4))
    assert len(fig.axes) == 2
    fig2 = viz.plot_detection(pcg.signal, pcg.fs, det)
    assert fig2.get_suptitle().startswith("S1/S2 detection")


def test_plot_metric_vs_snr():
    rows = [
        {"noise_type": n, "snr_in_db": s, "method": m, "s1_f1": 0.5 + 0.01 * s}
        for n in ("white", "hum")
        for s in (-5.0, 0.0, 5.0)
        for m in ("none", "bandpass", "mystery")
    ]
    fig = viz.plot_metric_vs_snr(rows, "s1_f1", "F1", "title")
    assert len(fig.axes) == 2
    assert len(fig.axes[0].lines) == 3
    fig2 = viz.plot_metric_vs_snr(rows, "s1_f1", "F1", "title", noise_types=["white", "pink"])
    assert len(fig2.axes[1].lines) == 0
    with pytest.raises(ValueError):
        viz.plot_metric_vs_snr([], "s1_f1", "F1", "title")
