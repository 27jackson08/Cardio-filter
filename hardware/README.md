# CardioFilter hardware prototype

A digital stethoscope for about **US$26** in parts, built from a conventional
acoustic chest piece, an electret microphone and a USB sound card. The design goal is
not to beat a commercial electronic stethoscope on raw sound quality, but to produce
recordings that are *good enough for the software to clean up*: the filtering and
S1/S2 detection in this repository are evaluated on exactly the kind of noise this
prototype picks up (mains hum, handling rumble, room noise, sensor hiss).

```
 chest piece ──► 8–10 cm silicone tube ──► 3D-printed coupler ──► electret capsule
                                                                       │
                           laptop ◄── USB sound card ◄── MAX4466 preamp ◄──┘
```

## Why this architecture

| Choice | Reason |
|---|---|
| Keep an acoustic chest piece | The diaphragm and bell already do the acoustic impedance matching from chest wall to air. Starting from a $6 stethoscope avoids designing a diaphragm. Electret-microphone stethoscopes in the literature take the same approach (Fernandes et al. 2018, Hasan et al. 2021). |
| Short tube, then a capsule | Tubing resonates and transmits handling noise. 8–10 cm keeps the capsule close to the chest piece while leaving room to hold the head. |
| Sealed 3D-printed coupler | The capsule sees pressure changes in a small air chamber instead of free-field sound. A TPU print also damps handling noise; a TPU diaphragm in direct contact with the air column performed best in a 2024 diaphragm study of electret stethoscopes. |
| Electret capsule + MAX4466 | Cheap, flat response down to ~20 Hz, no AGC (the MAX9814's automatic gain would distort the S1/S2 amplitude relationship the detector relies on). |
| USB sound card instead of a microcontroller ADC | Gives a proper anti-aliasing filter, 16-bit depth and 44.1 kHz capture for the price of an Arduino, and avoids writing firmware. The signal is decimated to 4 kHz in software to match CirCor. |

## Bill of materials

See [`bom.csv`](bom.csv). Total ≈ US$26; commercial electronic stethoscopes list
at US$300–500.

## Assembly

1. **Cut the tubing** 8–10 cm below the chest piece. Keep the chest piece end.
2. **Print the coupler** from [`coupler.scad`](coupler.scad) (OpenSCAD → STL). TPU
   is quieter; PETG is fine. Adjust `tube_id` and `capsule_d` to your parts.
3. **Press-fit the capsule** into the pocket at the back of the coupler with the
   sound port facing the air chamber. Route the two leads through the slot. A dab of
   hot glue around the back seals it.
4. **Push the tubing onto the barb.** It should be air-tight; a sealed system gives a
   much stronger low-frequency response.
5. **Wire the capsule to the MAX4466** (OUT → sound-card mic input, GND → ground,
   VCC → 3.3–5 V from the USB sound card or a USB port). Set the gain pot so that a
   normal heart beat peaks at about half scale when recording.
6. **Line the coupler** with felt where you hold it; most "noise" in a first
   recording is handling noise.

## Recording protocol

- Quiet room, subject seated or supine, 20 s per site.
- Record at the four standard sites used by CirCor: aortic (AV), pulmonic (PV),
  tricuspid (TV), mitral (MV). Name files `<subject>_<site>.wav`.
- Keep the mains adapter and phone chargers away from the probe cable; use the
  laptop on battery if hum is visible in the spectrogram.
- Hold the chest piece still for 2 s before you start; the detector uses the whole
  recording to estimate the cardiac period.

```bash
pip install "cardiofilter[record]"
python hardware/record.py --list
python hardware/record.py --device 2 --seconds 20 --out data/mine/s01_MV.wav
cardiofilter visualize data/mine/s01_MV.wav --out-dir figures/mine
```

## What to expect

- **Raw recording**: S1/S2 visible but sitting on 50/60 Hz hum and a low-frequency
  rumble from hand movement; room noise above 300 Hz.
- **After `bandpass`**: rumble and most room noise gone. Hum is inside the passband
  and remains.
- **After `bandpass+wavelet`**: sensor hiss within the passband reduced further;
  this is the default for `cardiofilter filter`.

The controlled-noise experiment (`cardiofilter experiment`) reports how much each
stage helps for each noise type, so you can decide which to use for your recordings.

## Safety

This is an educational prototype. It is not a medical device and must not be used for
diagnosis. Use only battery or USB power; never connect the probe to mains-powered
equipment without isolation.

## References

- Fernandes et al., "A low-cost digital stethoscope...", ISWCS 2018.
- Hasan et al., "A low-cost digital stethoscope for telemedicine", BMJ Innovations 2021.
- Diaphragm design for an electret microphone stethoscope, PMC 2024 (TPU diaphragm result).
- Oliveira et al., "The CirCor DigiScope Dataset", IEEE JBHI 2022 (recording protocol).
