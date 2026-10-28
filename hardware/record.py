"""Record heart sounds from the CardioFilter stethoscope prototype.

The prototype is an electret capsule coupled to a stethoscope chest piece and read
through a USB sound card, so any device that macOS/Linux/Windows sees as a microphone
works. Audio is captured at the device rate, decimated to 4 kHz (the CirCor rate, so
the same filters and detector apply) and written as 16-bit WAV.

Usage::

    pip install sounddevice            # or: pip install "cardiofilter[record]"
    python hardware/record.py --list   # find the USB sound card
    python hardware/record.py --device 2 --seconds 20 --out data/mine/subject01_MV.wav

Then::

    cardiofilter detect data/mine/subject01_MV.wav --plot subject01_MV.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy import signal as sps

from cardiofilter.io import save_wav

TARGET_FS = 4000


def decimate_to(signal: np.ndarray, fs_in: int, fs_out: int = TARGET_FS) -> np.ndarray:
    """Anti-aliased resampling to ``fs_out`` (polyphase, exact for integer ratios)."""
    if fs_in == fs_out:
        return np.asarray(signal, dtype=np.float64)
    from math import gcd

    g = gcd(fs_in, fs_out)
    return sps.resample_poly(np.asarray(signal, dtype=np.float64), fs_out // g, fs_in // g)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--list", action="store_true", help="list audio devices and exit")
    parser.add_argument("--device", type=int, default=None, help="input device index")
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--rate", type=int, default=44100, help="device sampling rate")
    parser.add_argument("--out", default="recording.wav")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        import sounddevice as sd
    except ImportError:
        print("sounddevice is not installed: pip install sounddevice", file=sys.stderr)
        return 2
    if args.list:
        print(sd.query_devices())
        return 0
    if args.seconds <= 0:
        print("--seconds must be positive", file=sys.stderr)
        return 2
    print(f"recording {args.seconds:.0f} s from device {args.device} at {args.rate} Hz ...")
    frames = int(args.seconds * args.rate)
    audio = sd.rec(frames, samplerate=args.rate, channels=1, dtype="float32", device=args.device)
    sd.wait()
    mono = decimate_to(audio[:, 0], args.rate, TARGET_FS)
    peak = float(np.max(np.abs(mono))) if mono.size else 0.0
    if peak == 0.0:
        print("captured silence; check the device index and microphone bias", file=sys.stderr)
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    save_wav(out, mono / peak * 0.9, TARGET_FS)
    print(f"wrote {out} ({len(mono) / TARGET_FS:.1f} s @ {TARGET_FS} Hz, peak {peak:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
