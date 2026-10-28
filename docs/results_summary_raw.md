# CardioFilter experiment summary

Records: 44. Noise types: ambient, hum, pink, rumble, white. Input SNRs (dB): -5, 0, 5, 10, 15. Detection tolerance: 100 ms.

## Detection on recordings as recorded (no added noise)

| method | n | s1_precision | s1_recall | s1_f1 | s2_precision | s2_recall | s2_f1 | s1_mae_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bandpass | 44 | 0.799 | 0.762 | 0.773 | 0.754 | 0.742 | 0.746 | 0.021 |
| bandpass+wavelet | 44 | 0.799 | 0.762 | 0.773 | 0.754 | 0.742 | 0.746 | 0.021 |
| none | 44 | 0.798 | 0.753 | 0.764 | 0.744 | 0.732 | 0.736 | 0.021 |
| wavelet | 44 | 0.801 | 0.750 | 0.765 | 0.744 | 0.732 | 0.736 | 0.020 |
| wavelet_bayes | 44 | 0.798 | 0.751 | 0.764 | 0.742 | 0.730 | 0.734 | 0.021 |

## Noise experiment, averaged over all noise types and SNRs

| method | n | snr_improvement_db | prd_percent | correlation | s1_f1 | s2_f1 |
| --- | --- | --- | --- | --- | --- | --- |
| bandpass | 1100 | -0.842 | 67.934 | 0.754 | 0.723 | 0.713 |
| bandpass+wavelet | 1100 | -0.838 | 67.902 | 0.754 | 0.722 | 0.712 |
| none | 1100 | 0.000 | 76.694 | 0.801 | 0.719 | 0.704 |
| wavelet | 1100 | 0.515 | 64.700 | 0.812 | 0.706 | 0.687 |
| wavelet_bayes | 1100 | 1.909 | 60.908 | 0.842 | 0.721 | 0.702 |

## Hardest condition (input SNR -5 dB)

| noise_type | method | snr_improvement_db | s1_f1 | s2_f1 |
| --- | --- | --- | --- | --- |
| ambient | bandpass | 8.952 | 0.754 | 0.763 |
| ambient | bandpass+wavelet | 8.985 | 0.750 | 0.760 |
| ambient | none | 0.000 | 0.696 | 0.675 |
| ambient | wavelet | 9.011 | 0.747 | 0.718 |
| ambient | wavelet_bayes | 6.044 | 0.726 | 0.694 |
| hum | bandpass | -0.383 | 0.506 | 0.580 |
| hum | bandpass+wavelet | -0.383 | 0.506 | 0.580 |
| hum | none | 0.000 | 0.536 | 0.584 |
| hum | wavelet | 0.179 | 0.491 | 0.533 |
| hum | wavelet_bayes | -0.001 | 0.532 | 0.580 |
| pink | bandpass | 4.875 | 0.634 | 0.663 |
| pink | bandpass+wavelet | 4.886 | 0.634 | 0.663 |
| pink | none | 0.000 | 0.585 | 0.595 |
| pink | wavelet | 1.211 | 0.561 | 0.574 |
| pink | wavelet_bayes | 0.575 | 0.591 | 0.597 |
| rumble | bandpass | 10.898 | 0.772 | 0.747 |
| rumble | bandpass+wavelet | 10.897 | 0.772 | 0.747 |
| rumble | none | 0.000 | 0.762 | 0.743 |
| rumble | wavelet | -0.048 | 0.725 | 0.699 |
| rumble | wavelet_bayes | -0.003 | 0.758 | 0.737 |
| white | bandpass | 5.889 | 0.629 | 0.620 |
| white | bandpass+wavelet | 5.914 | 0.630 | 0.619 |
| white | none | 0.000 | 0.591 | 0.601 |
| white | wavelet | 7.814 | 0.674 | 0.658 |
| white | wavelet_bayes | 9.389 | 0.631 | 0.611 |
