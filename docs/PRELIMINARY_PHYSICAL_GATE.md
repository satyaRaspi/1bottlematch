# Preliminary Physical Characteristics Gate — v1.5.7

This version adds a preliminary object-observation gate.

The gate compares broad physical characteristics of the registered bottle and the test sample before deeper matching.

Compared traits include:

- object height and width
- aspect ratio
- contour extent
- solidity
- perimeter
- top/mid/bottom width ratios
- shoulder slopes
- symmetry
- cap width and cap height
- label placement and label dimensions
- base width
- side profile
- top circularity
- DL/fallback mask bounding box and contour area

Decision rule:

```text
If Preliminary Physical Characteristics Gate fails = NO_MATCH
```

This gate catches obvious wrong-bottle cases before the final controlled geometry, color, DL and ML gates.
