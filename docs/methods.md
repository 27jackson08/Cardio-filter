# Methods

## Signal path

```
WAV (4 kHz) ─► noise injection (experiments only) ─► filter ─► Shannon envelope ─► peaks ─► S1/S2
                                                      │
                                                      └─► SNR / PRD / correlation vs. original
```

## Filters (`cardiofilter.filters`)

| Name | What it does | Parameters |
|---|---|---|
| `none` | Pass-through control | – |
| `bandpass` | 4th-order Butterworth, 25–400 Hz, zero-phase (`sosfiltfilt`) | `BandpassConfig(low_hz, high_hz, order)` |
| `wavelet` | DWT (`coif4`, 5 levels), universal soft threshold on all detail bands | `WaveletConfig(wavelet, level, rule, mode, scale)` |
| `wavelet_bayes` | As above with per-level BayesShrink thresholds | `rule="bayes"` |
| `bandpass+wavelet` | Bandpass first, then wavelet denoising | – |

Noise σ for the thresholds is the median absolute deviation of the finest detail
band divided by 0.6745.

## Noise models (`cardiofilter.noise`)

All generators return unit-variance noise; `mix_at_snr` scales it to the requested
input SNR relative to the recording's mean power.

| Name | Model | Mimics |
|---|---|---|
| `white` | Gaussian | ADC / preamp hiss |
| `pink` | 1/f-shaped Gaussian | Electronics and room noise |
| `hum` | 50 Hz + 2 decaying harmonics, random phase | Mains pickup |
| `rumble` | Gaussian low-passed at 20 Hz | Hand movement, breathing |
| `ambient` | Gaussian band-passed 300–1500 Hz | Speech, traffic, HVAC |

## Detector (`cardiofilter.detection`)

1. Bandpass 25–400 Hz.
2. Shannon energy envelope: 20 ms window, 10 ms hop, 30 ms moving-average smoothing,
   z-scored.
3. Cardiac period: autocorrelation of the homomorphic envelope (8 Hz low-pass on
   log-magnitude), restricted to 40–220 bpm; the shortest lag whose peak reaches 70 %
   of the tallest candidate wins.
4. Peaks: `scipy.signal.find_peaks` with prominence ≥ 0.2 σ and spacing
   ≥ max(120 ms, 0.3 × period).
5. Labels: each peak votes S1 if its following gap is shorter than its preceding
   gap (systole < diastole). For every peak, the alternating assignment that agrees
   with most votes among its 9 nearest peaks is used, so a missed beat only disturbs
   its neighbourhood.

## Metrics (`cardiofilter.metrics`)

- **SNR** (dB) of the filtered signal against the original recording;
  **SNR improvement** = SNR(filtered) − SNR(noisy).
- **PRD** (percent RMS difference) and **Pearson correlation** against the original.
- **Detection**: greedy one-to-one matching of detected to annotated S1 (and S2)
  midpoints within ±100 ms; precision, recall, F1 and mean absolute timing error.
  Detections outside annotated spans are discarded before scoring.

## Experiment grid (`cardiofilter experiment`)

For each annotated recording (trimmed to 30 s) × 5 noise types × 5 input SNRs
(−5, 0, 5, 10, 15 dB) × 5 methods. The same noise realisation is used for every
method within a cell so the comparison is paired. Outputs: `trials.csv` (one row per
trial), `summary.csv` (cell means), `dataset_eval.csv` (detection on the recordings
as recorded), three figures and `summary.md`.

## Reproducing

```bash
pip install -e ".[dev]"
cardiofilter download --dest data/circor --subjects 12     # ~15 MB
cardiofilter experiment --data data/circor/training_data --out results
```

Without the dataset: `cardiofilter experiment --synthetic 5 --out results-synthetic`.
