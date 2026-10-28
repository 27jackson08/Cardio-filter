# CardioFilter experiment summary

Records: 133. Noise types: ambient, hum, pink, rumble, white. Input SNRs (dB): -5, 5. Detection tolerance: 100 ms.

## Detection on recordings as recorded (no added noise)

| method | n | s1_precision | s1_recall | s1_f1 | s2_precision | s2_recall | s2_f1 | s1_mae_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bandpass | 133 | 0.791 | 0.774 | 0.776 | 0.760 | 0.755 | 0.753 | 0.025 |
| bandpass+wavelet | 133 | 0.802 | 0.762 | 0.773 | 0.759 | 0.742 | 0.744 | 0.025 |
| bandpass+wavelet_bayes | 133 | 0.791 | 0.773 | 0.776 | 0.761 | 0.756 | 0.754 | 0.025 |
| none | 133 | 0.790 | 0.765 | 0.770 | 0.764 | 0.753 | 0.752 | 0.025 |
| notch+bandpass | 133 | 0.791 | 0.774 | 0.776 | 0.760 | 0.755 | 0.753 | 0.025 |
| notch+bandpass+wavelet_bayes | 133 | 0.791 | 0.773 | 0.776 | 0.761 | 0.756 | 0.754 | 0.025 |
| wavelet | 133 | 0.794 | 0.752 | 0.763 | 0.754 | 0.734 | 0.738 | 0.025 |
| wavelet_bayes | 133 | 0.792 | 0.768 | 0.773 | 0.767 | 0.755 | 0.755 | 0.025 |

## Noise experiment, averaged over all noise types and SNRs

| method | n | snr_improvement_db | prd_percent | correlation | s1_f1 | s2_f1 |
| --- | --- | --- | --- | --- | --- | --- |
| bandpass | 1330 | 2.892 | 80.309 | 0.689 | 0.694 | 0.677 |
| bandpass+wavelet | 1330 | 2.607 | 81.008 | 0.652 | 0.690 | 0.652 |
| bandpass+wavelet_bayes | 1330 | 2.976 | 79.317 | 0.679 | 0.706 | 0.682 |
| none | 1330 | 0.000 | 117.031 | 0.681 | 0.689 | 0.671 |
| notch+bandpass | 1330 | 4.313 | 64.937 | 0.751 | 0.724 | 0.706 |
| notch+bandpass+wavelet_bayes | 1330 | 4.392 | 63.969 | 0.741 | 0.735 | 0.711 |
| wavelet | 1330 | 2.163 | 91.029 | 0.709 | 0.686 | 0.652 |
| wavelet_bayes | 1330 | 2.518 | 90.819 | 0.742 | 0.695 | 0.677 |

## Hardest condition (input SNR -5 dB)

| noise_type | method | snr_improvement_db | s1_f1 | s2_f1 |
| --- | --- | --- | --- | --- |
| ambient | bandpass | 8.881 | 0.732 | 0.716 |
| ambient | bandpass+wavelet | 7.275 | 0.754 | 0.672 |
| ambient | bandpass+wavelet_bayes | 8.034 | 0.766 | 0.710 |
| ambient | none | 0.000 | 0.687 | 0.667 |
| ambient | notch+bandpass | 8.881 | 0.732 | 0.716 |
| ambient | notch+bandpass+wavelet_bayes | 8.034 | 0.766 | 0.710 |
| ambient | wavelet | 8.727 | 0.751 | 0.669 |
| ambient | wavelet_bayes | 5.857 | 0.716 | 0.685 |
| hum | bandpass | -0.399 | 0.557 | 0.516 |
| hum | bandpass+wavelet | -0.270 | 0.569 | 0.533 |
| hum | bandpass+wavelet_bayes | -0.401 | 0.561 | 0.522 |
| hum | none | 0.000 | 0.566 | 0.541 |
| hum | notch+bandpass | 10.493 | 0.776 | 0.751 |
| hum | notch+bandpass+wavelet_bayes | 10.463 | 0.775 | 0.750 |
| hum | wavelet | 0.131 | 0.573 | 0.543 |
| hum | wavelet_bayes | 0.000 | 0.562 | 0.538 |
| pink | bandpass | 4.884 | 0.541 | 0.563 |
| pink | bandpass+wavelet | 6.546 | 0.540 | 0.530 |
| pink | bandpass+wavelet_bayes | 5.240 | 0.556 | 0.573 |
| pink | none | 0.000 | 0.533 | 0.539 |
| pink | notch+bandpass | 4.884 | 0.541 | 0.563 |
| pink | notch+bandpass+wavelet_bayes | 5.240 | 0.556 | 0.573 |
| pink | wavelet | 1.162 | 0.519 | 0.521 |
| pink | wavelet_bayes | 0.557 | 0.530 | 0.558 |
| rumble | bandpass | 10.865 | 0.774 | 0.756 |
| rumble | bandpass+wavelet | 10.610 | 0.774 | 0.748 |
| rumble | bandpass+wavelet_bayes | 10.832 | 0.777 | 0.757 |
| rumble | none | 0.000 | 0.781 | 0.754 |
| rumble | notch+bandpass | 10.865 | 0.774 | 0.756 |
| rumble | notch+bandpass+wavelet_bayes | 10.832 | 0.777 | 0.757 |
| rumble | wavelet | -0.034 | 0.772 | 0.747 |
| rumble | wavelet_bayes | -0.001 | 0.781 | 0.754 |
| white | bandpass | 5.834 | 0.569 | 0.574 |
| white | bandpass+wavelet | 6.768 | 0.597 | 0.586 |
| white | bandpass+wavelet_bayes | 7.511 | 0.640 | 0.624 |
| white | none | 0.000 | 0.564 | 0.579 |
| white | notch+bandpass | 5.834 | 0.569 | 0.574 |
| white | notch+bandpass+wavelet_bayes | 7.511 | 0.640 | 0.624 |
| white | wavelet | 7.566 | 0.591 | 0.584 |
| white | wavelet_bayes | 9.320 | 0.623 | 0.614 |
