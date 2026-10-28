"""Loading of heart-sound recordings and CirCor DigiScope segmentation annotations.

CirCor layout (``training_data/<subject>_<location>.*``):

- ``.wav`` – 16-bit PCM mono audio at 4000 Hz
- ``.tsv`` – segmentation rows ``start_s<TAB>end_s<TAB>label`` with labels
  ``0`` unannotated, ``1`` S1, ``2`` systole, ``3`` S2, ``4`` diastole
- ``.hea`` – WFDB header (not needed here)
- ``<subject>.txt`` – demographics, first line ``<subject> <n_locations> <fs>``
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import wavfile

LABEL_UNANNOTATED = 0
LABEL_S1 = 1
LABEL_SYSTOLE = 2
LABEL_S2 = 3
LABEL_DIASTOLE = 4

LABEL_NAMES = {
    LABEL_UNANNOTATED: "unannotated",
    LABEL_S1: "S1",
    LABEL_SYSTOLE: "systole",
    LABEL_S2: "S2",
    LABEL_DIASTOLE: "diastole",
}

AUSCULTATION_LOCATIONS = ("AV", "PV", "TV", "MV", "Phc")


@dataclass(frozen=True)
class Segmentation:
    """Segment-level annotations for one recording (times in seconds)."""

    starts: np.ndarray
    ends: np.ndarray
    labels: np.ndarray

    def __post_init__(self) -> None:
        if not (len(self.starts) == len(self.ends) == len(self.labels)):
            raise ValueError("starts, ends and labels must have equal length")
        if np.any(self.ends < self.starts):
            raise ValueError("segment end must not precede its start")

    def __len__(self) -> int:
        return len(self.labels)

    def event_times(self, label: int) -> np.ndarray:
        """Midpoints of every segment carrying ``label``."""
        mask = self.labels == label
        return 0.5 * (self.starts[mask] + self.ends[mask])

    @property
    def s1_times(self) -> np.ndarray:
        return self.event_times(LABEL_S1)

    @property
    def s2_times(self) -> np.ndarray:
        return self.event_times(LABEL_S2)

    def annotated_intervals(self) -> list[tuple[float, float]]:
        """Contiguous time spans that carry any non-zero label."""
        intervals: list[tuple[float, float]] = []
        for start, end, label in zip(self.starts, self.ends, self.labels, strict=True):
            if label == LABEL_UNANNOTATED:
                continue
            if intervals and abs(intervals[-1][1] - start) < 1e-6:
                intervals[-1] = (intervals[-1][0], float(end))
            else:
                intervals.append((float(start), float(end)))
        return intervals

    def is_annotated(self, times: np.ndarray) -> np.ndarray:
        """Boolean mask: does each time fall inside an annotated span?"""
        times = np.asarray(times, dtype=float)
        mask = np.zeros(times.shape, dtype=bool)
        for start, end in self.annotated_intervals():
            mask |= (times >= start) & (times <= end)
        return mask


@dataclass(frozen=True)
class Record:
    """One auscultation recording with optional annotations."""

    signal: np.ndarray
    fs: int
    name: str
    segmentation: Segmentation | None = None

    @property
    def duration(self) -> float:
        return len(self.signal) / self.fs


def load_wav(path: str | Path) -> tuple[np.ndarray, int]:
    """Load a mono WAV file as float64 in ``[-1, 1]``.

    Multi-channel files are averaged to mono. Integer PCM is scaled by its full-scale
    value; float WAVs are returned unchanged.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    fs, data = wavfile.read(path)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if np.issubdtype(data.dtype, np.integer):
        scale = float(np.iinfo(data.dtype).max)
        signal = data.astype(np.float64) / scale
    else:
        signal = data.astype(np.float64)
    return signal, int(fs)


def save_wav(path: str | Path, signal: np.ndarray, fs: int) -> Path:
    """Write ``signal`` (float in ``[-1, 1]``) as 16-bit PCM."""
    path = Path(path)
    clipped = np.clip(np.asarray(signal, dtype=np.float64), -1.0, 1.0)
    wavfile.write(path, int(fs), (clipped * 32767).astype(np.int16))
    return path


def load_segmentation(path: str | Path) -> Segmentation:
    """Parse a CirCor ``.tsv`` annotation file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.read_text().strip() == "":
        empty = np.zeros(0)
        return Segmentation(empty, empty.copy(), np.zeros(0, dtype=int))
    raw = np.loadtxt(path, delimiter="\t", ndmin=2)
    if raw.shape[1] != 3:
        raise ValueError(f"expected 3 columns in {path}, found {raw.shape[1]}")
    return Segmentation(
        starts=raw[:, 0].astype(float),
        ends=raw[:, 1].astype(float),
        labels=raw[:, 2].astype(int),
    )


def load_record(stem: str | Path) -> Record:
    """Load ``<stem>.wav`` and, when present, ``<stem>.tsv``.

    ``stem`` may be given with or without the ``.wav`` suffix.
    """
    stem = Path(stem)
    if stem.suffix == ".wav":
        stem = stem.with_suffix("")
    signal, fs = load_wav(stem.with_suffix(".wav"))
    tsv = stem.with_suffix(".tsv")
    segmentation = load_segmentation(tsv) if tsv.exists() else None
    return Record(signal=signal, fs=fs, name=stem.name, segmentation=segmentation)


def list_records(directory: str | Path, annotated_only: bool = True) -> list[Path]:
    """Return sorted recording stems (paths without suffix) found in ``directory``."""
    directory = Path(directory)
    stems = sorted(p.with_suffix("") for p in directory.glob("*.wav"))
    if annotated_only:
        stems = [s for s in stems if s.with_suffix(".tsv").exists()]
    return stems
