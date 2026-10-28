"""Download helpers for the CirCor DigiScope dataset (PhysioNet, ODC-By 1.0).

Only the public training split (v1.0.3, 3 120 annotated recordings from 942
subjects) is hosted; the challenge test split is withheld. Full download is ~560 MB,
so :func:`download_subset` fetches the first ``n_subjects`` subjects by default.

Citation: Oliveira J. et al., "The CirCor DigiScope Dataset: From Murmur Detection to
Murmur Classification", IEEE JBHI 2022. https://doi.org/10.13026/tshs-mw03
"""

from __future__ import annotations

import csv
import io
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path

PHYSIONET_BASE = "https://physionet.org/files/circor-heart-sound/1.0.3"
INDEX_CSV = "training_data.csv"
RECORDING_EXTENSIONS = (".wav", ".tsv", ".hea")

Fetch = Callable[[str], bytes]


def fetch(url: str, timeout_s: float = 60.0) -> bytes:
    """Download ``url`` and return its bytes."""
    if not url.startswith("https://"):
        raise ValueError("only https URLs are allowed")
    with urllib.request.urlopen(url, timeout=timeout_s) as response:  # noqa: S310
        return response.read()


def parse_index(csv_text: str) -> list[tuple[str, tuple[str, ...]]]:
    """Return ``(patient_id, locations)`` pairs from ``training_data.csv``."""
    reader = csv.DictReader(io.StringIO(csv_text))
    entries = []
    for row in reader:
        patient = (row.get("Patient ID") or "").strip()
        locations = (row.get("Recording locations:") or "").strip()
        if not patient or not locations:
            continue
        entries.append((patient, tuple(dict.fromkeys(locations.split("+")))))
    return entries


def plan_files(entries: Iterable[tuple[str, tuple[str, ...]]]) -> list[str]:
    """Relative file names needed for the given index entries."""
    names: list[str] = []
    for patient, locations in entries:
        names.append(f"{patient}.txt")
        for loc in locations:
            names.extend(f"{patient}_{loc}{ext}" for ext in RECORDING_EXTENSIONS)
    return names


def download_subset(
    dest: str | Path,
    n_subjects: int | None = 10,
    fetch_fn: Fetch = fetch,
    progress: Callable[[str], None] | None = None,
) -> list[Path]:
    """Download the index and the first ``n_subjects`` subjects into ``dest``.

    Existing files are skipped so the call can be resumed. Returns the paths written.
    """
    if n_subjects is not None and n_subjects < 1:
        raise ValueError("n_subjects must be >= 1 or None for all")
    dest = Path(dest)
    data_dir = dest / "training_data"
    data_dir.mkdir(parents=True, exist_ok=True)

    index_path = dest / INDEX_CSV
    if not index_path.exists():
        index_path.write_bytes(fetch_fn(f"{PHYSIONET_BASE}/{INDEX_CSV}"))
    entries = parse_index(index_path.read_text())
    if n_subjects is not None:
        entries = entries[:n_subjects]

    written: list[Path] = []
    for name in plan_files(entries):
        target = data_dir / name
        if target.exists():
            continue
        try:
            payload = fetch_fn(f"{PHYSIONET_BASE}/training_data/{name}")
        except OSError as exc:
            if progress:
                progress(f"skip {name}: {exc}")
            continue
        target.write_bytes(payload)
        written.append(target)
        if progress:
            progress(f"saved {name}")
    return written
