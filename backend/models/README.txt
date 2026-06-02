Place your optional real segmentation model here.

Options:
1. Ultralytics model (recommended for this build):
   - Example: yolov8n-seg.pt
   - Set env: BOTTLE_SEGMENTATION_MODEL_MODE=ultralytics
   - Optional env: BOTTLE_SEGMENTATION_MODEL_PATH=/full/path/to/yolov8n-seg.pt

2. ONNX model:
   - Example: bottle_segmentation.onnx
   - Set env: BOTTLE_SEGMENTATION_MODEL_MODE=onnx
   - Set env: BOTTLE_SEGMENTATION_MODEL_PATH=/full/path/to/bottle_segmentation.onnx
