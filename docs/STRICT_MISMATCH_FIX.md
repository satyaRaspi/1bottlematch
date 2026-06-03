# Strict Mismatch Fix — v1.6.0

This patch addresses false-positive matching between visually distinct objects, such as:

- transparent soda bottle
- opaque yellow bottle

Problem found:
Several older parameters were constant proxies, for example label top/height/width ratios and neck/cap ratios. Because these values were identical across objects, they could incorrectly pass even for different bottle classes.

Fixes:
- Added distinctive appearance features:
  - opaque surface score
  - transparent surface score
  - yellow dominance score
  - body saturation
  - whole object saturation
- Added Distinctive Object Appearance Gate.
- Tightened tolerance for appearance/color family features.
- Label ratios are now estimated from edge bands instead of being fixed constants.
- More obvious object class mismatches now become NO_MATCH.

Decision rule:
If Distinctive Object Appearance Gate fails = NO_MATCH.
