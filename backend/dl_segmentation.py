
"""
Light Deep-Learning Segmentation Layer
Version: 1.6.0
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
from runtime_config import enable_real_dl

_ULTRA_MODEL = None
_ULTRA_ERROR = None
_ONNX_SESSION = None
_ONNX_LOAD_ERROR = None

# COCO class id for bottle
BOTTLE_CLASS_IDS = {39}


def _mode() -> str:
    return os.environ.get("BOTTLE_SEGMENTATION_MODEL_MODE", "auto").strip().lower() or "auto"


def _model_path() -> str:
    return os.environ.get("BOTTLE_SEGMENTATION_MODEL_PATH", "").strip()


def _try_load_ultralytics():
    global _ULTRA_MODEL, _ULTRA_ERROR
    if not enable_real_dl():
        _ULTRA_ERROR = 'Real DL disabled by ENABLE_REAL_DL=false'
        return None
    if _ULTRA_MODEL is not None or _ULTRA_ERROR is not None:
        return _ULTRA_MODEL
    mode = _mode()
    if mode not in {"auto", "ultralytics", "yolo", "real"}:
        _ULTRA_ERROR = f"Ultralytics mode disabled by BOTTLE_SEGMENTATION_MODEL_MODE={mode}"
        return None
    try:
        from ultralytics import YOLO
        path = _model_path() or os.environ.get("ULTRALYTICS_BOTTLE_MODEL", "yolov8n-seg.pt")
        _ULTRA_MODEL = YOLO(path)
        return _ULTRA_MODEL
    except Exception as exc:
        _ULTRA_ERROR = str(exc)
        return None


def _try_load_onnx():
    global _ONNX_SESSION, _ONNX_LOAD_ERROR
    if not enable_real_dl():
        _ONNX_LOAD_ERROR = 'Real DL disabled by ENABLE_REAL_DL=false'
        return None
    if _ONNX_SESSION is not None or _ONNX_LOAD_ERROR is not None:
        return _ONNX_SESSION
    mode = _mode()
    if mode not in {"auto", "onnx"}:
        _ONNX_LOAD_ERROR = f"ONNX mode disabled by BOTTLE_SEGMENTATION_MODEL_MODE={mode}"
        return None
    model_path = _model_path()
    if not model_path:
        _ONNX_LOAD_ERROR = "BOTTLE_SEGMENTATION_MODEL_PATH not configured"
        return None
    if not Path(model_path).exists():
        _ONNX_LOAD_ERROR = f"Model file not found: {model_path}"
        return None
    try:
        import onnxruntime as ort
        _ONNX_SESSION = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        return _ONNX_SESSION
    except Exception as exc:
        _ONNX_LOAD_ERROR = str(exc)
        return None


def status() -> Dict:
    u = _try_load_ultralytics()
    o = _try_load_onnx()
    if u is not None:
        return {
            "dl_segmentation_enabled": True,
            "mode": "ultralytics_real_model",
            "model_path": _model_path() or os.environ.get("ULTRALYTICS_BOTTLE_MODEL", "yolov8n-seg.pt"),
            "note": "Using a real ultralytics segmentation model.",
            "load_error": None,
        }
    if o is not None:
        return {
            "dl_segmentation_enabled": True,
            "mode": "onnx_runtime_cpu",
            "model_path": _model_path(),
            "note": "Using ONNX Runtime CPU model.",
            "load_error": None,
        }
    return {
        "dl_segmentation_enabled": False,
        "mode": "opencv_grabcut_fallback",
        "model_path": _model_path(),
        "note": "No real model available. Using OpenCV GrabCut fallback.",
        "load_error": _ULTRA_ERROR or _ONNX_LOAD_ERROR,
    }


def _resize_keep(img: np.ndarray, size: int = 640) -> Tuple[np.ndarray, Tuple[int, int]]:
    h, w = img.shape[:2]
    return cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA), (w, h)


def _normalize_for_onnx(img: np.ndarray, size: int = 640) -> np.ndarray:
    resized, _ = _resize_keep(img, size)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    chw = np.transpose(rgb, (2, 0, 1))
    return np.expand_dims(chw, axis=0).astype(np.float32)


def _mask_from_onnx_output(outputs, original_shape):
    if not outputs:
        return None
    arr = np.asarray(outputs[0])
    while arr.ndim > 2:
        arr = arr[0]
    if arr.ndim != 2:
        return None
    arr = arr.astype(np.float32)
    if arr.max() > 1.0 or arr.min() < 0.0:
        arr = 1.0 / (1.0 + np.exp(-arr))
    mask = (arr > 0.5).astype(np.uint8) * 255
    h, w = original_shape[:2]
    mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
    return mask


def _ultralytics_segmentation(img: np.ndarray):
    model = _try_load_ultralytics()
    if model is None:
        return None, {"mode": "unavailable", "onnx_used": False, "error": _ULTRA_ERROR}
    try:
        results = model.predict(source=img, verbose=False, device='cpu')
        if not results:
            return None, {"mode": "ultralytics_real_model", "onnx_used": False, "error": 'No results'}
        r = results[0]
        if getattr(r, 'masks', None) is None or getattr(r, 'boxes', None) is None:
            return None, {"mode": "ultralytics_real_model", "onnx_used": False, "error": 'No masks or boxes returned'}
        masks = r.masks.data.cpu().numpy()
        classes = r.boxes.cls.cpu().numpy().astype(int) if r.boxes.cls is not None else np.array([], dtype=int)
        best_idx = None
        best_area = -1
        for idx, cls in enumerate(classes):
            if cls in BOTTLE_CLASS_IDS and idx < len(masks):
                area = float(np.sum(masks[idx] > 0.5))
                if area > best_area:
                    best_idx, best_area = idx, area
        if best_idx is None:
            # fallback to largest mask if any
            for idx in range(len(masks)):
                area = float(np.sum(masks[idx] > 0.5))
                if area > best_area:
                    best_idx, best_area = idx, area
        if best_idx is None:
            return None, {"mode": "ultralytics_real_model", "onnx_used": False, "error": 'No valid mask selected'}
        mask = (masks[best_idx] > 0.5).astype(np.uint8) * 255
        h, w = img.shape[:2]
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
        return mask, {"mode": "ultralytics_real_model", "onnx_used": False, "real_model_used": True, "error": None}
    except Exception as exc:
        return None, {"mode": "ultralytics_real_model", "onnx_used": False, "real_model_used": False, "error": str(exc)}


def _onnx_segmentation(img: np.ndarray):
    session = _try_load_onnx()
    if session is None:
        return None, {"mode": "onnx_runtime_cpu", "onnx_used": False, "error": _ONNX_LOAD_ERROR}
    try:
        input_name = session.get_inputs()[0].name
        tensor = _normalize_for_onnx(img)
        outputs = session.run(None, {input_name: tensor})
        mask = _mask_from_onnx_output(outputs, img.shape)
        if mask is None:
            return None, {"mode": "onnx_runtime_cpu", "onnx_used": False, "error": "Unsupported ONNX output format"}
        return mask, {"mode": "onnx_runtime_cpu", "onnx_used": True, "real_model_used": True, "error": None}
    except Exception as exc:
        return None, {"mode": "onnx_runtime_cpu", "onnx_used": False, "real_model_used": False, "error": str(exc)}


def _grabcut_fallback(img: np.ndarray):
    h, w = img.shape[:2]
    rect_margin_x = max(5, int(w * 0.08))
    rect_margin_y = max(5, int(h * 0.04))
    rect = (rect_margin_x, rect_margin_y, w - 2 * rect_margin_x, h - 2 * rect_margin_y)
    mask = np.zeros((h, w), np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(img, mask, rect, bgd, fgd, 3, cv2.GC_INIT_WITH_RECT)
        out = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    except Exception:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, a = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, b = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        out = a if np.mean(a > 0) < np.mean(b > 0) else b
    kernel = np.ones((5, 5), np.uint8)
    out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, kernel, iterations=2)
    out = cv2.morphologyEx(out, cv2.MORPH_OPEN, kernel, iterations=1)
    return out


def _largest_component(mask: np.ndarray) -> np.ndarray:
    n, labels, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
    if n <= 1:
        return mask
    areas = stats[1:, cv2.CC_STAT_AREA]
    idx = int(np.argmax(areas)) + 1
    return (labels == idx).astype(np.uint8) * 255


def _mask_stats(mask: np.ndarray) -> Dict:
    bin_mask = (mask > 0).astype(np.uint8)
    fill_ratio = float(np.mean(bin_mask))
    contours, _ = cv2.findContours(bin_mask * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return {
            'dl_mask_fill_ratio': 0.0,
            'dl_mask_bbox_x': 0.0,
            'dl_mask_bbox_y': 0.0,
            'dl_mask_bbox_w': 0.0,
            'dl_mask_bbox_h': 0.0,
            'dl_mask_contour_area': 0.0,
            'dl_mask_quality_score': 0.0,
        }
    c = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(c)
    area = float(cv2.contourArea(c))
    bbox_area = float(max(w*h,1))
    contour_extent = area / bbox_area
    quality = float(np.clip((contour_extent * 0.55) + (min(fill_ratio / 0.6, 1.0) * 0.25) + 0.20, 0.0, 1.0))
    return {
        'dl_mask_fill_ratio': fill_ratio,
        'dl_mask_bbox_x': float(x),
        'dl_mask_bbox_y': float(y),
        'dl_mask_bbox_w': float(w),
        'dl_mask_bbox_h': float(h),
        'dl_mask_contour_area': area,
        'dl_mask_quality_score': quality,
    }


def segment_bottle(img: np.ndarray):
    mask = None
    meta = {}
    # Prefer real model if possible
    if _mode() in {'auto','ultralytics','yolo','real'}:
        mask, meta = _ultralytics_segmentation(img)
    if mask is None and _mode() in {'auto','onnx'}:
        mask, meta = _onnx_segmentation(img)
    if mask is None:
        mask = _grabcut_fallback(img)
        meta = dict(meta or {})
        meta['mode'] = 'opencv_grabcut_fallback'
        meta['onnx_used'] = False
        meta['real_model_used'] = False
    mask = _largest_component(mask)
    meta.update(_mask_stats(mask))
    return mask, meta


def segmentation_features_from_image(img: np.ndarray, prefix: str = ''):
    mask, meta = segment_bottle(img)
    features = {}
    for key, val in meta.items():
        if isinstance(val, (int, float, bool)):
            features[f'{prefix}{key}'] = float(val)
    features[f'{prefix}dl_segmentation_enabled'] = 1.0 if meta.get('onnx_used') else 0.0
    features[f'{prefix}dl_segmentation_real_model_used'] = 1.0 if meta.get('real_model_used') else 0.0
    features[f'{prefix}dl_segmentation_fallback'] = 0.0 if (meta.get('onnx_used') or meta.get('real_model_used')) else 1.0
    return mask, features
