# Real Model Segmentation — v1.5.7

This build supports true model-based segmentation.

## Option 1 — Ultralytics YOLO Segmentation
Install optional dependencies:

```bash
pip install -r backend/requirements_real_dl.txt
```

Set environment variable:

```bash
export BOTTLE_SEGMENTATION_MODEL_MODE=ultralytics
```

Optional explicit model path:

```bash
export BOTTLE_SEGMENTATION_MODEL_PATH=/path/to/yolov8n-seg.pt
```

If no path is given, the code tries to use `yolov8n-seg.pt`.

## Option 2 — ONNX

```bash
export BOTTLE_SEGMENTATION_MODEL_MODE=onnx
export BOTTLE_SEGMENTATION_MODEL_PATH=/path/to/bottle_segmentation.onnx
```

## Fallback
If no model can be loaded, OpenCV GrabCut fallback is used automatically.
