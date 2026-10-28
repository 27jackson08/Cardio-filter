"""Command-line interface: ``cardiofilter <command> ...``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from cardiofilter import experiments as xp
from cardiofilter import visualize as viz
from cardiofilter.dataset import download_subset
from cardiofilter.detection import detect_heart_sounds
from cardiofilter.filters import FILTER_METHODS, apply_method
from cardiofilter.io import list_records, load_record, save_wav
from cardiofilter.noise import NOISE_TYPES
from cardiofilter.version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cardiofilter", description=__doc__)
    parser.add_argument("--version", action="version", version=f"cardiofilter {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_dl = sub.add_parser("download", help="download a CirCor DigiScope subset from PhysioNet")
    p_dl.add_argument("--dest", default="data/circor")
    p_dl.add_argument("--subjects", type=int, default=10, help="number of subjects (0 = all)")

    p_filter = sub.add_parser("filter", help="filter a WAV file and write the result")
    p_filter.add_argument("input")
    p_filter.add_argument("--method", choices=sorted(FILTER_METHODS), default="bandpass+wavelet")
    p_filter.add_argument("--out", required=True)

    p_det = sub.add_parser("detect", help="detect S1/S2 in a WAV file")
    p_det.add_argument("input", help="WAV path; a sibling .tsv is used for scoring if present")
    p_det.add_argument("--method", choices=sorted(FILTER_METHODS), default="bandpass")
    p_det.add_argument("--plot", help="write a detection figure to this PNG path")
    p_det.add_argument("--tolerance", type=float, default=xp.DEFAULT_TOLERANCE_S)

    p_vis = sub.add_parser("visualize", help="waveform, spectrogram and detection figures")
    p_vis.add_argument("input")
    p_vis.add_argument("--method", choices=sorted(FILTER_METHODS), default="bandpass+wavelet")
    p_vis.add_argument("--out-dir", default="figures")
    p_vis.add_argument("--seconds", type=float, default=6.0, help="window shown in waveform plots")

    p_exp = sub.add_parser("experiment", help="run the controlled-noise experiment grid")
    src = p_exp.add_mutually_exclusive_group(required=True)
    src.add_argument("--data", help="directory containing CirCor *.wav/*.tsv files")
    src.add_argument("--synthetic", type=int, metavar="N", help="use N synthetic records")
    p_exp.add_argument("--out", default="results")
    p_exp.add_argument("--max-records", type=int, default=None)
    p_exp.add_argument(
        "--noise", nargs="+", choices=sorted(NOISE_TYPES), default=list(xp.DEFAULT_NOISE_TYPES)
    )
    p_exp.add_argument("--snr", nargs="+", type=float, default=list(xp.DEFAULT_SNR_LEVELS))
    p_exp.add_argument(
        "--methods", nargs="+", choices=sorted(FILTER_METHODS), default=list(xp.DEFAULT_METHODS)
    )
    p_exp.add_argument("--max-duration", type=float, default=30.0)
    p_exp.add_argument("--seed", type=int, default=0)
    return parser


def cmd_download(args: argparse.Namespace) -> int:
    n = None if args.subjects == 0 else args.subjects
    written = download_subset(args.dest, n, progress=lambda m: print(m, file=sys.stderr))
    print(f"downloaded {len(written)} files to {Path(args.dest) / 'training_data'}")
    return 0


def cmd_filter(args: argparse.Namespace) -> int:
    record = load_record(args.input)
    filtered = apply_method(args.method, record.signal, record.fs)
    peak = np.max(np.abs(filtered))
    if peak > 1.0:
        filtered = filtered / peak
    save_wav(args.out, filtered, record.fs)
    print(f"wrote {args.out} ({args.method}, {record.duration:.1f} s @ {record.fs} Hz)")
    return 0


def cmd_detect(args: argparse.Namespace) -> int:
    record = load_record(args.input)
    filtered = apply_method(args.method, record.signal, record.fs)
    det = detect_heart_sounds(filtered, record.fs)
    print(
        f"{record.name}: {det.s1_times.size} S1, {det.s2_times.size} S2, "
        f"HR ~{det.heart_rate_bpm:.0f} bpm"
    )
    print("S1 (s): " + " ".join(f"{t:.3f}" for t in det.s1_times))
    print("S2 (s): " + " ".join(f"{t:.3f}" for t in det.s2_times))
    if record.segmentation is not None and len(record.segmentation):
        scores = xp.evaluate_detection(filtered, record.fs, record.segmentation, args.tolerance)
        print(
            f"S1 F1 {scores['s1_f1']:.3f}  S2 F1 {scores['s2_f1']:.3f}  "
            f"(tolerance {args.tolerance * 1000:.0f} ms)"
        )
    if args.plot:
        fig = viz.plot_detection(filtered, record.fs, det, record.segmentation, title=record.name)
        viz.save_figure(fig, args.plot)
        print(f"wrote {args.plot}")
    return 0


def cmd_visualize(args: argparse.Namespace) -> int:
    record = load_record(args.input)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    filtered = apply_method(args.method, record.signal, record.fs)
    window = (0.0, min(args.seconds, record.duration))
    det = detect_heart_sounds(filtered, record.fs)
    written = [
        viz.save_figure(
            viz.plot_waveform(
                {"raw": record.signal, args.method: filtered},
                record.fs,
                title=record.name,
                time_range=window,
            ),
            str(out / f"{record.name}_waveform.png"),
        ),
        viz.save_figure(
            viz.plot_spectrogram(record.signal, record.fs, title=f"{record.name} raw"),
            str(out / f"{record.name}_spectrogram_raw.png"),
        ),
        viz.save_figure(
            viz.plot_spectrogram(filtered, record.fs, title=f"{record.name} {args.method}"),
            str(out / f"{record.name}_spectrogram_filtered.png"),
        ),
        viz.save_figure(
            viz.plot_detection(
                filtered, record.fs, det, record.segmentation, title=record.name, time_range=window
            ),
            str(out / f"{record.name}_detection.png"),
        ),
    ]
    for path in written:
        print(f"wrote {path}")
    return 0


def _load_records(args: argparse.Namespace) -> list:
    if args.synthetic is not None:
        return xp.synthetic_records(args.synthetic, seed=args.seed)
    stems = list_records(args.data)
    if args.max_records is not None:
        stems = stems[: args.max_records]
    if not stems:
        raise SystemExit(f"no annotated recordings found in {args.data}")
    return [load_record(stem) for stem in stems]


def cmd_experiment(args: argparse.Namespace) -> int:
    records = _load_records(args)
    config = xp.ExperimentConfig(
        noise_types=tuple(args.noise),
        snr_levels_db=tuple(args.snr),
        methods=tuple(args.methods),
        seed=args.seed,
        max_duration_s=args.max_duration,
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"evaluating {len(records)} records as recorded ...", file=sys.stderr)
    baseline = xp.evaluate_dataset(records, config)
    xp.write_csv(baseline, out / "dataset_eval.csv")
    baseline_summary = xp.summarize(baseline, by=["method"])

    print(
        f"running noise grid: {len(config.noise_types)} noises x "
        f"{len(config.snr_levels_db)} SNRs x {len(config.methods)} methods ...",
        file=sys.stderr,
    )
    results = xp.run_experiment(records, config)
    rows = xp.results_to_rows(results)
    xp.write_csv(rows, out / "trials.csv")
    by_cell = xp.summarize(rows, by=["noise_type", "snr_in_db", "method"])
    xp.write_csv(by_cell, out / "summary.csv")
    by_method = xp.summarize(rows, by=["method"])

    viz.save_figure(
        viz.plot_metric_vs_snr(
            by_cell, "snr_improvement_db", "SNR improvement (dB)", "Signal quality after filtering"
        ),
        str(out / "snr_improvement.png"),
    )
    viz.save_figure(
        viz.plot_metric_vs_snr(by_cell, "s1_f1", "S1 detection F1", "S1 detection accuracy"),
        str(out / "s1_f1.png"),
    )
    viz.save_figure(
        viz.plot_metric_vs_snr(by_cell, "s2_f1", "S2 detection F1", "S2 detection accuracy"),
        str(out / "s2_f1.png"),
    )

    report = _report(len(records), config, baseline_summary, by_method, by_cell)
    (out / "summary.md").write_text(report)
    print(report)
    return 0


def _report(n_records: int, config: xp.ExperimentConfig, baseline, by_method, by_cell) -> str:
    detect_cols = [
        "method",
        "n",
        "s1_precision",
        "s1_recall",
        "s1_f1",
        "s2_precision",
        "s2_recall",
        "s2_f1",
        "s1_mae_s",
    ]
    quality_cols = [
        "method",
        "n",
        "snr_improvement_db",
        "prd_percent",
        "correlation",
        "s1_f1",
        "s2_f1",
    ]
    hardest = [r for r in by_cell if float(r["snr_in_db"]) == min(config.snr_levels_db)]
    hard_cols = ["noise_type", "method", "snr_improvement_db", "s1_f1", "s2_f1"]
    return "\n".join(
        [
            "# CardioFilter experiment summary",
            "",
            f"Records: {n_records}. Noise types: {', '.join(config.noise_types)}. "
            f"Input SNRs (dB): {', '.join(f'{s:g}' for s in config.snr_levels_db)}. "
            f"Detection tolerance: {config.tolerance_s * 1000:.0f} ms.",
            "",
            "## Detection on recordings as recorded (no added noise)",
            "",
            xp.markdown_table(baseline, detect_cols, digits=3),
            "",
            "## Noise experiment, averaged over all noise types and SNRs",
            "",
            xp.markdown_table(by_method, quality_cols, digits=3),
            "",
            f"## Hardest condition (input SNR {min(config.snr_levels_db):g} dB)",
            "",
            xp.markdown_table(hardest, hard_cols, digits=3),
            "",
        ]
    )


COMMANDS = {
    "download": cmd_download,
    "filter": cmd_filter,
    "detect": cmd_detect,
    "visualize": cmd_visualize,
    "experiment": cmd_experiment,
}


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return COMMANDS[args.command](args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
