# Research notes

Background reading that shaped the design. Each decision in the code points back to
one of these.

## 1. The problem

Auscultation is cheap and universal, but a stethoscope recording made outside a
clinic contains the chest wall's signal plus everything the probe and room add:
mains interference, handling and breathing rumble, speech and traffic, and the
electronics' own hiss. Individual heart sounds, S1 (mitral/tricuspid closure) and S2
(aortic/pulmonic closure), are short (50–100 ms) and quiet, so moderate noise is enough
to hide them. The question CardioFilter asks is practical: with a $26 probe, how much
of that can software recover, and which method should run first?

## 2. Where heart sounds live in frequency

| Component | Dominant band | Notes |
|---|---|---|
| S1 | 20–100 Hz (energy up to ~150 Hz) | Longer, lower-pitched, louder at the apex |
| S2 | 50–150 Hz (up to ~200 Hz) | Shorter, sharper, louder at the base |
| Murmurs | 100–600 Hz | Broadband; the CirCor task focuses on these |
| Motion / respiration artefacts | < 20 Hz | Large amplitude, easily removed |
| Mains hum | 50/60 Hz + harmonics | Sits *inside* the S1/S2 band |
| Room noise, speech | 300 Hz – several kHz | Mostly outside the band |

Consequence: a bandpass of roughly **25–400 Hz** removes rumble and most room noise
but cannot remove hum or in-band hiss. That is the gap wavelet thresholding is meant
to fill.

## 3. Filtering methods compared

### Butterworth bandpass

Standard pre-processing in nearly every PCG paper, including the Springer HSMM
segmentation algorithm that underlies the PhysioNet 2016/2022 baselines
(25–400 Hz, 4th order, zero-phase). We implement it with second-order sections and
forward-backward filtering so S1/S2 timing is not shifted.

### Wavelet denoising

Messer, Agzarian & Abbott (2001) were the first to study wavelet families and
thresholds specifically for PCG noise removal and found the `coif`/`db` families with
soft thresholding at 5+ levels effective. The threshold is the key design choice:

- **Universal / VisuShrink** (Donoho & Johnstone 1994): `σ·sqrt(2 ln N)` with `σ`
  from the median absolute deviation of the finest detail band. One threshold for all
  levels; tends to over-smooth.
- **BayesShrink** (Chang, Yu & Vetterli 2000): a per-level threshold `σ²/σ_x` that
  adapts to how much signal each band holds; gentler on bands with strong signal.

Both are implemented; the universal rule is the default because it was the more
robust of the two in the controlled-noise grid.

A wavelet denoiser *keeps* a component if its coefficients are large. Hum at 50 Hz
produces large coefficients in the 31–62 Hz band at 4 kHz, so wavelets cannot remove
it either; that limitation shows up clearly in the results and motivates a notch
filter as future work.

## 4. Locating S1 and S2

### Envelope

Liang, Lukkarinen & Hartimo (1997) introduced the **normalised average Shannon
energy** envelope, `−x² log x²` averaged over 20 ms windows with a 10 ms hop. It
emphasises medium-intensity components and suppresses both noise floor and spikes,
which is why nearly every envelope-based S1/S2 detector since has used it.

The **homomorphic envelope** (exp of the low-passed log-magnitude) is smoother; we use
it only for estimating the cardiac period by autocorrelation, where smoothness helps,
and the Shannon envelope for peak picking, where sharpness helps.

### Labelling

The classic rule is that systole (S1→S2) is shorter than diastole (S2→S1). It holds
comfortably at adult resting rates but weakens above ~120 bpm where the two intervals
converge. CirCor is a paediatric dataset with a median rate near 110 bpm, so this is
the dominant error source in our detector. On the development subset the interval
rule chose the right S1/S2 assignment on 36 of 44 recordings; a spectral-centroid
rule (S2 has more high-frequency energy) managed only 29, so the interval rule was
kept.

State-of-the-art segmentation (Springer et al. 2016 logistic-regression HSMM; the
PhysioNet 2022 winner's RNN+HSMM, McDonald et al. 2024) treats the four states
S1→systole→S2→diastole jointly with duration priors. That is the natural next step
if envelope peak picking proves limiting.

## 5. Dataset

**CirCor DigiScope** (Oliveira et al., IEEE JBHI 2022; PhysioNet v1.0.3):
5 272 recordings from 1 568 paediatric subjects (0–21 y) collected in two screening
campaigns in Northeast Brazil, 4 000 Hz, one recording per auscultation site
(AV, PV, TV, MV, other). The public training split contains 3 120 recordings from
942 subjects with semi-automatic, expert-corrected segmentation annotations
(S1 / systole / S2 / diastole / unannotated). The remaining recordings are held
back as the PhysioNet 2022 challenge test set. Licence: ODC Attribution 1.0.

We use the segmentation annotations as ground truth for S1/S2 detection, scoring
inside annotated spans only, with the 100 ms tolerance used by Springer et al.

## 6. Low-cost hardware

Electret-microphone stethoscopes are well established: a 3D-printed chest piece with
an embedded electret feeding a smartphone (IEEE 2016), a ~US$5 build with a TPU
diaphragm (PMC 2024), an Arduino Mega build at 10 % of the Littmann price (2019),
and a BMJ Innovations retrofit of a conventional stethoscope (2021). Common findings:
electrets are cheap and adequately flat but sensitive to ambient noise, and a sealed
air path matters more than the microphone. Our prototype follows the retrofit route
(acoustic chest piece + capsule + USB audio) so that the acoustic design is already
solved and the effort goes into signal processing.

## References

- Liang H., Lukkarinen S., Hartimo I. "Heart sound segmentation algorithm based on
  heart sound envelogram." Computers in Cardiology 1997.
- Messer S.R., Agzarian J., Abbott D. "Optimal wavelet denoising for phonocardiograms."
  Microelectronics Journal 32 (2001).
- Donoho D.L., Johnstone I.M. "Ideal spatial adaptation by wavelet shrinkage."
  Biometrika 81 (1994).
- Chang S.G., Yu B., Vetterli M. "Adaptive wavelet thresholding for image denoising
  and compression." IEEE Trans. Image Processing 9 (2000).
- Springer D.B., Tarassenko L., Clifford G.D. "Logistic regression-HSMM-based heart
  sound segmentation." IEEE Trans. Biomed. Eng. 63 (2016).
- Oliveira J. et al. "The CirCor DigiScope Dataset: From Murmur Detection to Murmur
  Classification." IEEE J. Biomed. Health Inform. 26 (2022). PhysioNet
  https://doi.org/10.13026/tshs-mw03
- Reyna M.A. et al. "Heart murmur detection from phonocardiogram recordings: The
  George B. Moody PhysioNet Challenge 2022." PLOS Digital Health (2023).
- McDonald A., Gales M.J.F., Agarwal A. "A recurrent neural network and parallel
  hidden Markov model algorithm to segment and detect heart murmurs in
  phonocardiograms." PLOS Digital Health 3 (2024).
- Fernandes et al. ISWCS 2018; Hasan et al. BMJ Innovations 2021; "Diaphragm design
  for an electret microphone stethoscope", PMC 2024 (hardware references).
