"""Plotting helpers: waveforms, spectrograms, envelopes with S1/S2 markers, and
experiment summaries.

All functions return a :class:`matplotlib.figure.Figure` so callers decide whether to
save or show it. Colours are assigned per entity (method or noise type) in a fixed
order so the same method keeps the same hue across every figure.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from scipy import signal as sps  # noqa: E402

from cardiofilter.detection import Detection  # noqa: E402
from cardiofilter.io import Segmentation  # noqa: E402

CATEGORICAL = (
    "#2a78d6",
    "#eb6834",
    "#1baf7a",
    "#eda100",
    "#e87ba4",
    "#008300",
    "#6250d6",
    "#e34948",
)
"""Fixed categorical hue order (colour-vision-deficiency safe for adjacent pairs)."""

METHOD_COLORS: Mapping[str, str] = {
    "none": "#52514e",
    "bandpass": CATEGORICAL[0],
    "wavelet": CATEGORICAL[1],
    "wavelet_bayes": CATEGORICAL[2],
    "bandpass+wavelet": CATEGORICAL[3],
    "bandpass+wavelet_bayes": CATEGORICAL[4],
    "notch+bandpass": CATEGORICAL[5],
    "notch+bandpass+wavelet_bayes": CATEGORICAL[6],
}
S1_COLOR = CATEGORICAL[0]
S2_COLOR = CATEGORICAL[1]
REFERENCE_COLOR = "#52514e"
GRID_STYLE = {"color": "#d9d8d3", "linewidth": 0.6}


def _style(ax: plt.Axes) -> None:
    ax.grid(True, **GRID_STYLE)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)


def plot_waveform(
    signals: Mapping[str, np.ndarray],
    fs: int,
    title: str = "Heart sound waveform",
    time_range: tuple[float, float] | None = None,
) -> Figure:
    """Stack one axis per named signal (e.g. raw vs filtered)."""
    if not signals:
        raise ValueError("signals must not be empty")
    fig, axes = plt.subplots(len(signals), 1, figsize=(11, 2.2 * len(signals)), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, (name, x), colour in zip(axes, signals.items(), CATEGORICAL, strict=False):
        t = np.arange(len(x)) / fs
        if time_range is not None:
            keep = (t >= time_range[0]) & (t <= time_range[1])
            t, x = t[keep], np.asarray(x)[keep]
        ax.plot(t, x, color=colour, linewidth=0.7)
        ax.set_ylabel(name)
        _style(ax)
    if time_range is not None:
        axes[-1].set_xlim(*time_range)
    axes[-1].set_xlabel("Time (s)")
    axes[0].set_title(title)
    fig.tight_layout()
    return fig


def plot_spectrogram(
    x: np.ndarray,
    fs: int,
    title: str = "Spectrogram",
    max_freq_hz: float = 800.0,
    window_s: float = 0.064,
) -> Figure:
    """Log-power spectrogram limited to the heart-sound band."""
    x = np.asarray(x, dtype=np.float64)
    nperseg = max(int(window_s * fs), 16)
    if len(x) < nperseg:
        raise ValueError("signal shorter than the spectrogram window")
    f, t, sxx = sps.spectrogram(x, fs=fs, nperseg=nperseg, noverlap=nperseg * 3 // 4)
    keep = f <= max_freq_hz
    power_db = 10.0 * np.log10(sxx[keep] + 1e-12)
    fig, ax = plt.subplots(figsize=(11, 3.2))
    mesh = ax.pcolormesh(t, f[keep], power_db, shading="gouraud", cmap="Blues", rasterized=True)
    fig.colorbar(mesh, ax=ax, label="Power (dB)")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_title(title)
    fig.tight_layout()
    return fig


def plot_detection(
    x: np.ndarray,
    fs: int,
    detection: Detection,
    segmentation: Segmentation | None = None,
    title: str = "S1/S2 detection",
    time_range: tuple[float, float] | None = None,
) -> Figure:
    """Waveform with the envelope and detected (and optionally annotated) S1/S2."""
    t = np.arange(len(x)) / fs
    if time_range is not None:
        keep = (t >= time_range[0]) & (t <= time_range[1])
        t, x = t[keep], np.asarray(x)[keep]
    fig, (ax_sig, ax_env) = plt.subplots(2, 1, figsize=(11, 5), sharex=True)
    ax_sig.plot(t, x, color="#7a7975", linewidth=0.6, label="signal")
    ax_env.plot(
        detection.envelope.times,
        detection.envelope.values,
        color="#0b0b0b",
        linewidth=1.2,
        label="Shannon envelope",
    )
    for ax in (ax_sig, ax_env):
        for s1 in detection.s1_times:
            ax.axvline(s1, color=S1_COLOR, linewidth=1.4, alpha=0.9)
        for s2 in detection.s2_times:
            ax.axvline(s2, color=S2_COLOR, linewidth=1.4, alpha=0.9, linestyle="--")
    if segmentation is not None:
        y = ax_sig.get_ylim()[1] * 0.9
        ax_sig.scatter(
            segmentation.s1_times,
            np.full(len(segmentation.s1_times), y),
            marker="v",
            color=S1_COLOR,
            s=36,
            label="annotated S1",
        )
        ax_sig.scatter(
            segmentation.s2_times,
            np.full(len(segmentation.s2_times), y),
            marker="v",
            facecolors="none",
            edgecolors=S2_COLOR,
            s=36,
            label="annotated S2",
        )
    ax_sig.plot([], [], color=S1_COLOR, linewidth=1.4, label="detected S1")
    ax_sig.plot([], [], color=S2_COLOR, linewidth=1.4, linestyle="--", label="detected S2")
    ax_sig.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=5, fontsize=8, frameon=False)
    ax_sig.set_ylabel("Amplitude")
    ax_env.set_ylabel("Envelope (z)")
    ax_env.set_xlabel("Time (s)")
    fig.suptitle(f"{title}  (estimated HR {detection.heart_rate_bpm:.0f} bpm)")
    for ax in (ax_sig, ax_env):
        _style(ax)
    if time_range is not None:
        ax_env.set_xlim(*time_range)
    fig.tight_layout()
    return fig


def plot_metric_vs_snr(
    rows: Sequence[Mapping[str, object]],
    metric: str,
    ylabel: str,
    title: str,
    noise_types: Sequence[str] | None = None,
) -> Figure:
    """Small multiples (one per noise type): ``metric`` against input SNR, one line per method.

    ``rows`` are summary rows with keys ``noise_type``, ``snr_in_db``, ``method`` and
    ``metric``.
    """
    if not rows:
        raise ValueError("rows must not be empty")
    kinds = list(noise_types) if noise_types else sorted({str(r["noise_type"]) for r in rows})
    methods = sorted(
        {str(r["method"]) for r in rows},
        key=lambda m: list(METHOD_COLORS).index(m) if m in METHOD_COLORS else 99,
    )
    fig, axes = plt.subplots(1, len(kinds), figsize=(3.6 * len(kinds), 3.4), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, kind in zip(axes, kinds, strict=True):
        for i, method in enumerate(methods):
            pts = sorted(
                (float(r["snr_in_db"]), float(r[metric]))
                for r in rows
                if r["noise_type"] == kind and r["method"] == method
            )
            if not pts:
                continue
            xs, ys = zip(*pts, strict=True)
            colour = METHOD_COLORS.get(method, CATEGORICAL[i % len(CATEGORICAL)])
            ax.plot(xs, ys, marker="o", markersize=4, linewidth=1.8, color=colour, label=method)
        ax.set_title(kind)
        ax.set_xlabel("Input SNR (dB)")
        _style(ax)
    axes[0].set_ylabel(ylabel)
    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle(title)
    fig.tight_layout()
    return fig


def save_figure(fig: Figure, path: str, dpi: int = 130) -> str:
    """Save and close a figure; returns the path."""
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path
