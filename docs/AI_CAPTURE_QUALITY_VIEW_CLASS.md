# AI Capture Quality + View Validation + Object Class Detection — v1.6.0

This version adds a lightweight AI-assisted validation layer.

Features:

1. Capture Quality Assistant
- blur check
- brightness check
- contrast check
- glare check
- object centered check
- object size check
- multiple object check

2. View Validation
- validates front image
- validates side image
- validates top image
- detects duplicate images uploaded in multiple slots

3. Object Class Detection
Detected classes:
- transparent_bottle
- opaque_bottle
- amber_glass_bottle
- yellow_opaque_bottle
- can_or_carton_like
- non_bottle_or_unknown

4. Matching Gate
During comparison, the observed sample is checked against the registered bottle's stored AI capture profile.

If the observed capture is poor or object class differs, result becomes:

```text
NO_MATCH
```

New endpoint:

```text
POST /signature/capture-ai-preview
```
