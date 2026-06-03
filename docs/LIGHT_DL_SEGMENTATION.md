# Light Deep-Learning Segmentation — v1.6.0

Adds optional ONNX Runtime CPU segmentation with OpenCV GrabCut fallback.

## API

GET /dl/status

## Configuration

To use a real model, install ONNX Runtime and set:

```bash
pip install onnxruntime
export BOTTLE_SEGMENTATION_MODEL_PATH=/path/to/model.onnx
```

Without a model, the app uses OpenCV fallback and still runs locally/Railway.

The physical signature engine remains the source of truth.
