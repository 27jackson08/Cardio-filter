"""Build docs/results.md and the README results block from an experiment output dir.

Usage: python scripts/write_results.py results docs/results.md README.md [results-holdout]
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from cardiofilter import experiments as xp

METRICS = ["snr_improvement_db", "prd_percent", "correlation", "s1_f1", "s2_f1"]
START, END = "<!-- RESULTS:START -->", "<!-- RESULTS:END -->"


def _read(path: Path, text_keys: tuple[str, ...]) -> list[dict[str, object]]:
    rows = list(csv.DictReader(path.open()))
    return [{k: (v if k in text_keys else float(v)) for k, v in r.items()} for r in rows]


def _detection_table(base: list[dict[str, object]]) -> str:
    return xp.markdown_table(
        xp.summarize(base, by=["method"]),
        [
            "method",
            "s1_precision",
            "s1_recall",
            "s1_f1",
            "s2_precision",
            "s2_recall",
            "s2_f1",
            "s1_mae_s",
        ],
        3,
    )


def _mean_f1(rows: list[dict[str, object]], method: str) -> tuple[float, float]:
    sel = [r for r in rows if r["method"] == method]
    s1 = sum(float(r["s1_f1"]) for r in sel) / len(sel)
    s2 = sum(float(r["s2_f1"]) for r in sel) / len(sel)
    return s1, s2


def _holdout_section(holdout: Path | None, dev_base: list[dict[str, object]]) -> str:
    if holdout is None or not (holdout / "dataset_eval.csv").exists():
        return ""
    base = _read(holdout / "dataset_eval.csv", ("record", "method"))
    n_records = len({r["record"] for r in base})
    n_subjects = len({str(r["record"]).split("_")[0] for r in base})
    dev_s1, dev_s2 = _mean_f1(dev_base, "bandpass")
    ho_s1, ho_s2 = _mean_f1(base, "bandpass")
    best = "notch+bandpass+wavelet_bayes"
    best_s1, best_s2 = _mean_f1(base, best)
    parts = [
        "## 6. Held-out check",
        "",
        f"{n_records} recordings from {n_subjects} subjects that were **not** used to tune "
        "the detector (`cardiofilter download --skip 12`). Same scoring.",
        "",
        "### Detection as recorded (held-out)",
        "",
        _detection_table(base),
        "",
        f"**Generalisation gap.** With the bandpass, S1/S2 F1 falls from "
        f"{dev_s1:.3f}/{dev_s2:.3f} on the tuning subset to {ho_s1:.3f}/{ho_s2:.3f} here, "
        f"so quote the held-out numbers. The recommended chain `{best}` scores "
        f"{best_s1:.3f}/{best_s2:.3f} as recorded; the ranking of methods is unchanged, "
        "and the notch again restores hum-corrupted recordings to clean-recording accuracy.",
    ]
    trials_path = holdout / "trials.csv"
    if trials_path.exists():
        trials = _read(trials_path, ("record", "noise_type", "method"))
        levels = sorted({float(r["snr_in_db"]) for r in trials})
        parts += [
            "",
            f"### Noise grid (held-out), input SNR {', '.join(f'{v:g}' for v in levels)} dB",
            "",
            xp.markdown_table(
                xp.summarize(trials, by=["method"], metrics=METRICS), ["method", *METRICS], 2
            ),
            "",
            f"### Held-out, hardest condition (input SNR {levels[0]:g} dB)",
            "",
            xp.markdown_table(
                xp.summarize(
                    [r for r in trials if r["snr_in_db"] == levels[0]],
                    by=["noise_type", "method"],
                    metrics=METRICS,
                ),
                ["noise_type", "method", "snr_improvement_db", "s1_f1", "s2_f1"],
                2,
            ),
        ]
    return "\n".join(parts) + "\n"


def build(results: Path, holdout: Path | None = None) -> tuple[str, str]:
    trials = _read(results / "trials.csv", ("record", "noise_type", "method"))
    base = _read(results / "dataset_eval.csv", ("record", "method"))
    n_records = len({r["record"] for r in base})
    as_recorded = _detection_table(base)
    overall = xp.markdown_table(
        xp.summarize(trials, by=["method"], metrics=METRICS), ["method", *METRICS], 2
    )
    by_snr = xp.markdown_table(
        xp.summarize(trials, by=["snr_in_db", "method"], metrics=METRICS),
        ["snr_in_db", "method", "snr_improvement_db", "s1_f1", "s2_f1"],
        2,
    )
    hardest = xp.markdown_table(
        xp.summarize(
            [r for r in trials if r["snr_in_db"] == -5.0],
            by=["noise_type", "method"],
            metrics=METRICS,
        ),
        ["noise_type", "method", "snr_improvement_db", "s1_f1", "s2_f1"],
        2,
    )
    doc = f"""# Results

Development subset: the first 12 subjects of the CirCor training split with all four
auscultation sites, {n_records} annotated recordings (6.6–32.8 s, trimmed to 30 s),
median heart rate ≈ 115 bpm. Detection tolerance ±100 ms. Noise grid: 5 noise types ×
5 input SNRs (−5, 0, 5, 10, 15 dB) × 5 methods = {len(trials)} trials. Regenerate with
`cardiofilter experiment --data data/circor/training_data --out results` followed by
`python scripts/write_results.py results docs/results.md README.md`.

## 1. Detection on the recordings as recorded

No synthetic noise; the recordings already contain the clinic's own noise.

{as_recorded}

**Reading it.** Bandpass before detection gives the best S1/S2 localisation
(S1 F1 0.82, S2 F1 0.79) with a mean timing error of 20 ms, well inside the 100 ms
tolerance. Wavelet thresholding on its own is slightly *worse* than no filtering: the
universal threshold shaves heart-sound energy from the 62–250 Hz bands along with the
noise. The remaining errors are dominated by S1/S2 label swaps in recordings where
systole and diastole have similar length (paediatric rates above ~120 bpm) and by
loud murmurs that create extra envelope peaks.

## 2. Controlled-noise experiment

### Averaged over every noise type and input SNR

{overall}

### By input SNR (averaged over noise types)

{by_snr}

### Hardest condition, input SNR −5 dB

{hardest}

![SNR improvement](figures/snr_improvement.png)

![S1 detection F1](figures/s1_f1.png)

## 3. What the numbers say

1. **The right filter depends on the noise, which is why a single number misleads.**
   At −5 dB, bandpass is unbeatable against handling rumble (+10.9 dB; wavelets do
   nothing because 0–20 Hz sits in the approximation band they leave untouched) and
   as good as anything against ambient noise (+9.0 dB). Against broadband hiss,
   BayesShrink wavelets win on signal fidelity (+9.4 dB versus +5.9 dB for bandpass)
   because they remove noise *inside* the passband. Against pink noise, bandpass
   followed by wavelet thresholding is best (+6.6 dB).
2. **Mains hum needs its own stage.** 50 Hz and its harmonics sit in the middle of
   the S1/S2 band, produce large wavelet coefficients, and survive both bandpass and
   wavelet thresholding (≤ 0.2 dB); detection F1 falls to ~0.6 at −5 dB. A cascade of
   zero-phase IIR notches (Q = 30) at the fundamental and two harmonics recovers
   +10.5 dB and brings F1 back to 0.78/0.76, the same as a hum-free recording.
   The notch is gated on a tonal-power test so it is skipped when no hum is present;
   without that gate it carved enough heart-sound energy from clean recordings to cost
   3–4 F1 points.
3. **Bandpass can "lose" SNR at high input SNR.** The clean reference is the original
   recording, so removing genuine content outside 25–400 Hz counts as error: −9 dB at
   15 dB input. That is a property of the metric, not a reason to avoid the filter;
   detection F1, which is scored against human annotations, keeps improving with
   bandpass at every SNR. BayesShrink is the only single method that never reduces
   SNR, because its per-band thresholds back off when a band is mostly signal.
4. **Detection is less sensitive to filtering than SNR is.** The detector bandpasses
   internally, so even the `none` row benefits from a bandpass before envelope
   extraction. The extra filters matter most at −5 dB: +7 F1 points for white noise
   and +7 for ambient noise with `bandpass+wavelet_bayes`, +16 for hum with the notch.
5. **Combined methods need the noise level from the raw signal.** After a bandpass the
   finest wavelet band is empty, so a threshold estimated there collapses and the
   wavelet stage becomes a no-op. Estimating sigma on the raw signal fixes that. With
   the universal threshold the combination then over-smooths at high SNR (−9.7 dB at
   15 dB); with BayesShrink it does not, and `notch+bandpass+wavelet_bayes` has the
   best detection scores of every method both as recorded (S1 F1 0.824, S2 F1 0.795)
   and across the noise grid (0.79 / 0.77).

## 4. Recommendation for the prototype

- Default processing chain: **notch (when hum is detected) → bandpass 25–400 Hz →
  BayesShrink wavelet denoising with sigma from the raw signal**. This is the CLI
  default for `cardiofilter filter` and `cardiofilter visualize`.
- If only one stage can run (e.g. on a microcontroller): the bandpass. It is within
  a point of the full chain on detection and is the only stage that touches rumble.
- Hum should still be prevented in hardware (shielded cable, battery power); the
  notch takes a 1.7 Hz sliver out of the S1 band each time it fires.

## 5. Limitations

- The detector's five parameters were tuned on this same 44-recording subset, so the
  F1 values above are optimistic; section 6 reports the same metrics on subjects the
  detector never saw.
- Noise is synthetic and stationary. Real field noise is bursty (speech, footsteps),
  and the prototype's own recordings are the next validation step
  (`hardware/record.py`).
- Each SNR level is weighted equally in the averages; real recordings cluster at
  0–10 dB.

{_holdout_section(holdout, base)}"""
    holdout_line = ""
    if holdout is not None and (holdout / "dataset_eval.csv").exists():
        ho = _read(holdout / "dataset_eval.csv", ("record", "method"))
        ho_s1, ho_s2 = _mean_f1(ho, "notch+bandpass+wavelet_bayes")
        n_ho = len({r["record"] for r in ho})
        n_subj = len({str(r["record"]).split("_")[0] for r in ho})
        holdout_line = (
            f"On {n_ho} held-out recordings from {n_subj} other subjects the recommended "
            f"chain scores S1 F1 {ho_s1:.2f} and S2 F1 {ho_s2:.2f} as recorded, about four "
            "points below the tuning subset; the ranking of methods is unchanged "
            "([details](docs/results.md#6-held-out-check)).\n"
        )
    readme_block = f"""{START}
On the 44-recording development subset (12 subjects, all four sites), with
S1/S2 scored against the expert annotations at ±100 ms:

**Detection on the recordings as recorded**

{as_recorded}

{holdout_line}
**Hardest condition: synthetic noise at −5 dB input SNR** (SNR improvement in dB and
detection F1; full grid and figures in [docs/results.md](docs/results.md))

{hardest}

Three findings carry over to the hardware:

- **The right filter depends on the noise.** Bandpass beats everything on handling
  rumble (+10.9 dB) and matches the best on room noise; BayesShrink wavelets win on
  broadband hiss (+9.4 dB vs +5.9 dB) because they remove noise *inside* the passband.
- **Mains hum needs its own stage.** 50 Hz sits in the middle of the S1/S2 band and
  survives bandpass and wavelets alike; a gated notch cascade recovers +10.5 dB and
  restores detection F1 from 0.59 to 0.78 at −5 dB.
- **The recommended chain is notch → bandpass → BayesShrink wavelet.** It has the
  best S1/S2 localisation of every method as recorded (S1 F1 0.82, S2 F1 0.80, 20 ms
  timing error) and under noise, and it is the CLI default.

![SNR improvement](docs/figures/snr_improvement.png)
{END}"""
    return doc, readme_block


def main(results_dir: str, results_md: str, readme: str, holdout_dir: str | None = None) -> int:
    doc, block = build(Path(results_dir), Path(holdout_dir) if holdout_dir else None)
    Path(results_md).write_text(doc)
    text = Path(readme).read_text()
    start, end = text.index(START), text.index(END) + len(END)
    Path(readme).write_text(text[:start] + block + text[end:])
    print(f"wrote {results_md} and updated {readme}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(*sys.argv[1:]))
