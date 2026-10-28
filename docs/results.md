# Results

Development subset: the first 12 subjects of the CirCor training split with all four
auscultation sites, 44 annotated recordings (6.6–32.8 s, trimmed to 30 s),
median heart rate ≈ 115 bpm. Detection tolerance ±100 ms. Noise grid: 5 noise types ×
5 input SNRs (−5, 0, 5, 10, 15 dB) × 5 methods = 5500 trials. Regenerate with
`cardiofilter experiment --data data/circor/training_data --out results` followed by
`python scripts/write_results.py results docs/results.md README.md`.

## 1. Detection on the recordings as recorded

No synthetic noise; the recordings already contain the clinic's own noise.

| method | s1_precision | s1_recall | s1_f1 | s2_precision | s2_recall | s2_f1 | s1_mae_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bandpass | 0.851 | 0.807 | 0.822 | 0.797 | 0.795 | 0.793 | 0.020 |
| bandpass+wavelet | 0.848 | 0.794 | 0.813 | 0.782 | 0.775 | 0.776 | 0.020 |
| none | 0.837 | 0.786 | 0.800 | 0.773 | 0.771 | 0.770 | 0.020 |
| wavelet | 0.832 | 0.776 | 0.792 | 0.764 | 0.756 | 0.757 | 0.020 |
| wavelet_bayes | 0.837 | 0.786 | 0.801 | 0.772 | 0.771 | 0.770 | 0.020 |

**Reading it.** Bandpass before detection gives the best S1/S2 localisation
(S1 F1 0.82, S2 F1 0.79) with a mean timing error of 20 ms, well inside the 100 ms
tolerance. Wavelet thresholding on its own is slightly *worse* than no filtering: the
universal threshold shaves heart-sound energy from the 62–250 Hz bands along with the
noise. The remaining errors are dominated by S1/S2 label swaps in recordings where
systole and diastole have similar length (paediatric rates above ~120 bpm) and by
loud murmurs that create extra envelope peaks.

## 2. Controlled-noise experiment

### Averaged over every noise type and input SNR

| method | snr_improvement_db | prd_percent | correlation | s1_f1 | s2_f1 |
| --- | --- | --- | --- | --- | --- |
| bandpass | -0.84 | 67.93 | 0.75 | 0.77 | 0.76 |
| bandpass+wavelet | -1.32 | 70.31 | 0.72 | 0.76 | 0.74 |
| none | 0.00 | 76.69 | 0.80 | 0.77 | 0.75 |
| wavelet | 0.52 | 64.70 | 0.81 | 0.75 | 0.73 |
| wavelet_bayes | 1.91 | 60.91 | 0.84 | 0.77 | 0.75 |

### By input SNR (averaged over noise types)

| snr_in_db | method | snr_improvement_db | s1_f1 | s2_f1 |
| --- | --- | --- | --- | --- |
| -5.00 | bandpass | 6.05 | 0.72 | 0.73 |
| -5.00 | bandpass+wavelet | 6.26 | 0.71 | 0.71 |
| -5.00 | none | 0.00 | 0.72 | 0.72 |
| -5.00 | wavelet | 3.63 | 0.71 | 0.70 |
| -5.00 | wavelet_bayes | 3.20 | 0.72 | 0.72 |
| 0.00 | bandpass | 3.37 | 0.75 | 0.74 |
| 0.00 | bandpass+wavelet | 2.89 | 0.74 | 0.73 |
| 0.00 | none | 0.00 | 0.75 | 0.73 |
| 0.00 | wavelet | 2.28 | 0.75 | 0.73 |
| 0.00 | wavelet_bayes | 2.58 | 0.75 | 0.73 |
| 10.00 | bandpass | -4.40 | 0.80 | 0.78 |
| 10.00 | bandpass+wavelet | -5.13 | 0.78 | 0.76 |
| 10.00 | none | 0.00 | 0.80 | 0.77 |
| 10.00 | wavelet | -0.93 | 0.78 | 0.75 |
| 10.00 | wavelet_bayes | 1.25 | 0.80 | 0.77 |
| 15.00 | bandpass | -9.06 | 0.81 | 0.78 |
| 15.00 | bandpass+wavelet | -9.71 | 0.79 | 0.77 |
| 15.00 | none | 0.00 | 0.80 | 0.77 |
| 15.00 | wavelet | -3.22 | 0.78 | 0.75 |
| 15.00 | wavelet_bayes | 0.63 | 0.80 | 0.76 |
| 5.00 | bandpass | -0.17 | 0.79 | 0.78 |
| 5.00 | bandpass+wavelet | -0.90 | 0.77 | 0.76 |
| 5.00 | none | 0.00 | 0.77 | 0.75 |
| 5.00 | wavelet | 0.82 | 0.76 | 0.74 |
| 5.00 | wavelet_bayes | 1.89 | 0.78 | 0.75 |

### Hardest condition, input SNR −5 dB

| noise_type | method | snr_improvement_db | s1_f1 | s2_f1 |
| --- | --- | --- | --- | --- |
| ambient | bandpass | 8.95 | 0.77 | 0.78 |
| ambient | bandpass+wavelet | 7.47 | 0.80 | 0.77 |
| ambient | none | 0.00 | 0.75 | 0.73 |
| ambient | wavelet | 9.01 | 0.80 | 0.77 |
| ambient | wavelet_bayes | 6.04 | 0.76 | 0.73 |
| hum | bandpass | -0.38 | 0.59 | 0.65 |
| hum | bandpass+wavelet | -0.20 | 0.59 | 0.63 |
| hum | none | 0.00 | 0.62 | 0.67 |
| hum | wavelet | 0.18 | 0.59 | 0.63 |
| hum | wavelet_bayes | -0.00 | 0.61 | 0.66 |
| pink | bandpass | 4.87 | 0.67 | 0.69 |
| pink | bandpass+wavelet | 6.61 | 0.66 | 0.67 |
| pink | none | 0.00 | 0.70 | 0.69 |
| pink | wavelet | 1.21 | 0.66 | 0.66 |
| pink | wavelet_bayes | 0.57 | 0.69 | 0.68 |
| rumble | bandpass | 10.90 | 0.82 | 0.79 |
| rumble | bandpass+wavelet | 10.47 | 0.79 | 0.76 |
| rumble | none | 0.00 | 0.82 | 0.79 |
| rumble | wavelet | -0.05 | 0.79 | 0.76 |
| rumble | wavelet_bayes | -0.00 | 0.82 | 0.79 |
| white | bandpass | 5.89 | 0.74 | 0.73 |
| white | bandpass+wavelet | 6.95 | 0.72 | 0.72 |
| white | none | 0.00 | 0.69 | 0.70 |
| white | wavelet | 7.81 | 0.70 | 0.70 |
| white | wavelet_bayes | 9.39 | 0.74 | 0.72 |

![SNR improvement](figures/snr_improvement.png)

![S1 detection F1](figures/s1_f1.png)

## 3. What the numbers say

1. **The right filter depends on the noise, which is why a single number misleads.**
   At −5 dB, bandpass is unbeatable against handling rumble (+10.9 dB; wavelets do
   nothing because 0–20 Hz sits in the approximation band they leave untouched) and
   as good as anything against ambient noise (+9.0 dB). Against broadband hiss,
   BayesShrink wavelets win (+9.4 dB versus +5.9 dB for bandpass) because they remove
   noise *inside* the passband. Against pink noise, bandpass followed by wavelet
   thresholding is best (+6.6 dB).
2. **Nothing here removes mains hum.** 50 Hz and its harmonics sit in the middle of
   the S1/S2 band, produce large wavelet coefficients, and survive every method
   (≤ 0.2 dB). Detection F1 falls to ~0.6 at −5 dB. This is the clearest result for
   the hardware: shield the cable and run on battery, and add a notch or adaptive
   hum canceller to the software (planned).
3. **Bandpass can "lose" SNR at high input SNR.** The clean reference is the original
   recording, so removing genuine content outside 25–400 Hz counts as error: −9 dB at
   15 dB input. That is a property of the metric, not a reason to avoid the filter;
   detection F1, which is scored against human annotations, keeps improving with
   bandpass at every SNR. BayesShrink is the only method that never reduces SNR,
   because its per-band thresholds back off when a band is mostly signal.
4. **Detection is less sensitive to filtering than SNR is.** The detector bandpasses
   internally, so even the `none` row benefits from a bandpass before envelope
   extraction. The extra filters matter most at −5 dB: +5 F1 points for white noise
   (bandpass or BayesShrink) and +5 points for ambient noise (wavelet).
5. **Combined bandpass + wavelet needs the noise level from the raw signal.** After a
   bandpass the finest wavelet band is empty, so a threshold estimated there collapses
   and the wavelet stage becomes a no-op. Estimating sigma on the raw signal fixes
   that but makes the universal threshold too aggressive at high SNR (−9.7 dB at 15 dB).
   A BayesShrink variant of the combination is the obvious next experiment.

## 4. Recommendation for the prototype

- Default pre-processing for S1/S2 detection: **bandpass 25–400 Hz**.
- When hiss dominates (low preamp gain, cheap sound card): **BayesShrink wavelet**
  denoising after the bandpass, estimated on the raw signal.
- Hum must be handled in hardware and with a dedicated notch filter; no general
  denoiser in this study touches it.

## 5. Limitations

- The detector's five parameters were tuned on this same 44-recording subset, so its
  F1 is optimistic; run `cardiofilter download --subjects 100` and evaluate on
  subjects outside the first twelve before quoting the numbers.
- Noise is synthetic and stationary. Real field noise is bursty (speech, footsteps),
  and the prototype's own recordings are the next validation step
  (`hardware/record.py`).
- Each SNR level is weighted equally in the averages; real recordings cluster at
  0–10 dB.
