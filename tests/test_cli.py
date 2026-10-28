from pathlib import Path

import numpy as np
import pytest

from cardiofilter import cli
from cardiofilter.io import save_wav
from cardiofilter.synth import generate_pcg


@pytest.fixture
def wav_with_tsv(tmp_path: Path) -> Path:
    pcg = generate_pcg(duration=6.0, heart_rate=70.0, seed=2)
    path = tmp_path / "demo_MV.wav"
    save_wav(path, pcg.signal, pcg.fs)
    rows = [f"{t - 0.02:.4f}\t{t + 0.02:.4f}\t1" for t in pcg.s1_times]
    rows += [f"{t - 0.02:.4f}\t{t + 0.02:.4f}\t3" for t in pcg.s2_times]
    (tmp_path / "demo_MV.tsv").write_text("\n".join(sorted(rows)) + "\n")
    return path


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert "cardiofilter" in capsys.readouterr().out


def test_filter_command_writes_wav(wav_with_tsv, tmp_path, capsys):
    out = tmp_path / "filtered.wav"
    assert cli.main(["filter", str(wav_with_tsv), "--method", "wavelet", "--out", str(out)]) == 0
    assert out.exists()
    assert "wrote" in capsys.readouterr().out


def test_detect_command_scores_and_plots(wav_with_tsv, tmp_path, capsys):
    plot = tmp_path / "det.png"
    assert cli.main(["detect", str(wav_with_tsv), "--plot", str(plot)]) == 0
    out = capsys.readouterr().out
    assert "S1 F1" in out and plot.exists()


def test_visualize_command(wav_with_tsv, tmp_path, capsys):
    out_dir = tmp_path / "figs"
    assert cli.main(["visualize", str(wav_with_tsv), "--out-dir", str(out_dir)]) == 0
    assert len(list(out_dir.glob("*.png"))) == 4


def test_experiment_command_synthetic(tmp_path, capsys):
    out = tmp_path / "results"
    argv = [
        "experiment",
        "--synthetic",
        "1",
        "--out",
        str(out),
        "--noise",
        "white",
        "--snr",
        "5",
        "--methods",
        "none",
        "bandpass",
        "--max-duration",
        "4",
    ]
    assert cli.main(argv) == 0
    for name in (
        "trials.csv",
        "summary.csv",
        "summary.md",
        "dataset_eval.csv",
        "snr_improvement.png",
        "s1_f1.png",
        "s2_f1.png",
    ):
        assert (out / name).exists(), name
    assert "# CardioFilter experiment summary" in capsys.readouterr().out


def test_experiment_command_with_data_dir(wav_with_tsv, tmp_path):
    out = tmp_path / "results"
    argv = [
        "experiment",
        "--data",
        str(wav_with_tsv.parent),
        "--out",
        str(out),
        "--noise",
        "hum",
        "--snr",
        "0",
        "--methods",
        "bandpass",
        "--max-records",
        "1",
        "--max-duration",
        "4",
    ]
    assert cli.main(argv) == 0
    assert (out / "trials.csv").read_text().count("demo_MV") == 1


def test_experiment_command_empty_dir(tmp_path):
    with pytest.raises(SystemExit):
        cli.main(["experiment", "--data", str(tmp_path), "--out", str(tmp_path / "r")])


def test_download_command_uses_fetch(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        cli, "download_subset", lambda dest, n, progress=None: [Path("a"), Path("b")]
    )
    assert cli.main(["download", "--dest", str(tmp_path), "--subjects", "0"]) == 0
    assert "downloaded 2 files" in capsys.readouterr().out
    assert np is not None
