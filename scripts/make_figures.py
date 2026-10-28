"""Regenerate the README figures from one CirCor recording.

Usage: python scripts/make_figures.py data/circor/training_data/29045_MV.wav docs/figures
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from cardiofilter import visualize as viz
from cardiofilter.detection import detect_heart_sounds
from cardiofilter.filters import apply_method
from cardiofilter.io import load_record
from cardiofilter.noise import make_noise, mix_at_snr

WINDOW = (0.0, 5.0)


def main(wav: str, out_dir: str) -> int:
    record = load_record(wav)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)

    # A realistic field mixture: hum + hiss + handling rumble at 0 dB overall.
    n = len(record.signal)
    mixture = (
        make_noise("hum", n, record.fs, rng)
        + make_noise("white", n, record.fs, rng)
        + make_noise("rumble", n, record.fs, rng)
    )
    noisy = mix_at_snr(record.signal, mixture, 0.0)
    stages = {
        "original": record.signal,
        "noisy (0 dB)": noisy,
        "bandpass": apply_method("bandpass", noisy, record.fs),
        "bandpass+wavelet": apply_method("bandpass+wavelet", noisy, record.fs),
    }
    viz.save_figure(
        viz.plot_waveform(
            stages, record.fs, title=f"{record.name}: filtering stages", time_range=WINDOW
        ),
        str(out / "filtering_stages.png"),
    )
    viz.save_figure(
        viz.plot_spectrogram(
            noisy, record.fs, title=f"{record.name}: noisy (hum + hiss + rumble, 0 dB)"
        ),
        str(out / "spectrogram_noisy.png"),
    )
    viz.save_figure(
        viz.plot_spectrogram(
            stages["bandpass+wavelet"], record.fs, title=f"{record.name}: bandpass+wavelet"
        ),
        str(out / "spectrogram_denoised.png"),
    )
    det = detect_heart_sounds(stages["bandpass+wavelet"], record.fs)
    viz.save_figure(
        viz.plot_detection(
            stages["bandpass+wavelet"],
            record.fs,
            det,
            record.segmentation,
            title=f"{record.name}: detection after denoising",
            time_range=WINDOW,
        ),
        str(out / "detection_denoised.png"),
    )
    print(f"wrote 4 figures to {out}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
