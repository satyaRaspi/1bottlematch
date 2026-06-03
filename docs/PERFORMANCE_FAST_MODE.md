# Performance Fast Mode — v1.6.0

This build is optimized for demo and Railway deployment.

Default settings:

```text
BOTTLE_PROCESSING_MODE=fast
MAX_IMAGE_DIM=720
ENABLE_OVERLAYS=true
ENABLE_REAL_DL=false
DETAILED_PARAMETER_TRACE=false
```

For fastest processing:

```bash
export ENABLE_OVERLAYS=false
export ENABLE_REAL_DL=false
export DETAILED_PARAMETER_TRACE=false
export MAX_IMAGE_DIM=640
```

Enable deep analysis only when required:

```bash
export ENABLE_REAL_DL=true
export DETAILED_PARAMETER_TRACE=true
```
