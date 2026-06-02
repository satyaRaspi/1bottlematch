# Performance Fast Mode — v1.5.7

The app became slow after adding OCR, overlays, real-DL hooks and detailed per-parameter processing status.

This version adds performance toggles.

Default fast settings:

```text
BOTTLE_PROCESSING_MODE=fast
MAX_IMAGE_DIM=720
ENABLE_OCR=true
ENABLE_OVERLAYS=true
ENABLE_REAL_DL=false
DETAILED_PARAMETER_TRACE=false
```

What changed:

- OCR is on by default.
- Real DL model loading is off by default.
- Images are resized before heavy processing.
- Detailed per-parameter scrolling trace is off by default.
- Overlay generation can be disabled if needed.

Enable deep analysis only when required:

```bash
export ENABLE_OCR=true
export ENABLE_REAL_DL=true
export DETAILED_PARAMETER_TRACE=true
```

For fastest processing:

```bash
export ENABLE_OVERLAYS=false
export ENABLE_OCR=true
export ENABLE_REAL_DL=false
export DETAILED_PARAMETER_TRACE=false
export MAX_IMAGE_DIM=640
```
