
"""
AI Capture Quality, View Validation and Object Class Detection
Version: 1.6.0

This is a lightweight AI-assisted rules/vision layer. It avoids heavy deep-learning
runtime dependencies and works on CPU/Railway/local setups.

It provides:
1. Capture quality score
2. Recapture-required reasons
3. Front/side/top view validation
4. Duplicate view detection
5. Multiple object detection
6. Object class prediction:
   - transparent_bottle
   - opaque_bottle
   - amber_glass_bottle
   - yellow_opaque_bottle
   - can_or_carton_like
   - non_bottle_or_unknown
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple, List
from pathlib import Path
import cv2
import numpy as np


def _load(path: Optional[str]):
    if not path:
        return None
    img = cv2.imread(str(path))
    if img is None or img.size == 0:
        return None
    return img


def _resize(img, max_dim=720):
    h, w = img.shape[:2]
    m = max(h, w)
    if m <= max_dim:
        return img
    s = max_dim / m
    return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)


def _simple_mask(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, a = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, b = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    def best_score(mask):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return -1
        c = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(c)
        x, y, w, h = cv2.boundingRect(c)
        center = 1 - abs((x + w/2) - img.shape[1]/2) / max(img.shape[1], 1)
        fill = area / max(img.shape[0] * img.shape[1], 1)
        return center * 0.55 + min(fill / 0.55, 1.0) * 0.45

    mask = a if best_score(a) >= best_score(b) else b
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    return mask


def _largest_contour(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, []
    return max(contours, key=cv2.contourArea), contours


def _laplacian_sharpness(gray):
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _brightness_contrast(gray):
    return float(np.mean(gray) / 255.0), float(np.std(gray) / 128.0)


def _glare_score(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    v = hsv[:, :, 2]
    s = hsv[:, :, 1]
    # bright low-saturation patches approximate glare
    glare = ((v > 235) & (s < 55)).mean()
    return float(np.clip(glare * 8.0, 0.0, 1.0))


def _perceptual_hash(img):
    gray = cv2.cvtColor(_resize(img, 128), cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (16, 16), interpolation=cv2.INTER_AREA)
    med = np.median(small)
    return (small > med).astype(np.uint8).flatten()


def _hash_similarity(a, b):
    if a is None or b is None:
        return 0.0
    return float(1.0 - np.mean(a != b))


def _object_stats(img):
    img = _resize(img)
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = _simple_mask(img)
    contour, contours = _largest_contour(mask)

    if contour is None:
        return {
            "mask_found": False,
            "contour_count": 0,
            "bbox": [0, 0, 0, 0],
            "bbox_area_ratio": 0.0,
            "aspect": 0.0,
            "fill_ratio": 0.0,
            "solidity": 0.0,
            "center_offset": 1.0,
            "sharpness": _laplacian_sharpness(gray),
            "brightness": _brightness_contrast(gray)[0],
            "contrast": _brightness_contrast(gray)[1],
            "glare_score": _glare_score(img),
            "hash": _perceptual_hash(img),
            "median_saturation": 0.0,
            "median_value": 0.0,
            "yellow_score": 0.0,
            "amber_score": 0.0,
        }

    x, y, bw, bh = cv2.boundingRect(contour)
    area = float(cv2.contourArea(contour))
    bbox_area = max(float(bw * bh), 1.0)
    hull = cv2.convexHull(contour)
    hull_area = max(float(cv2.contourArea(hull)), 1.0)
    solidity = area / hull_area
    aspect = float(bh / max(bw, 1))
    fill_ratio = area / max(h * w, 1)
    center_offset = abs((x + bw/2) - w/2) / max(w, 1)

    pts = img[mask > 0]
    if pts.size == 0:
        pts = img.reshape((-1, 3))
    hsv = cv2.cvtColor(pts.reshape((-1, 1, 3)).astype("uint8"), cv2.COLOR_BGR2HSV).reshape((-1, 3))
    sat = float(np.median(hsv[:, 1]) / 255.0)
    val = float(np.median(hsv[:, 2]) / 255.0)
    hue = hsv[:, 0].astype(np.float32)
    yellow_score = float(np.mean((hue >= 20) & (hue <= 40) & (hsv[:,1] > 70)))
    amber_score = float(np.mean((hue >= 8) & (hue <= 25) & (hsv[:,1] > 50)))

    brightness, contrast = _brightness_contrast(gray)

    return {
        "mask_found": True,
        "contour_count": len([c for c in contours if cv2.contourArea(c) > (h*w*0.02)]),
        "bbox": [int(x), int(y), int(bw), int(bh)],
        "bbox_area_ratio": float(bbox_area / max(h*w, 1)),
        "aspect": aspect,
        "fill_ratio": float(fill_ratio),
        "solidity": float(solidity),
        "center_offset": float(center_offset),
        "sharpness": _laplacian_sharpness(gray),
        "brightness": brightness,
        "contrast": contrast,
        "glare_score": _glare_score(img),
        "hash": _perceptual_hash(img),
        "median_saturation": sat,
        "median_value": val,
        "yellow_score": yellow_score,
        "amber_score": amber_score,
    }


def _view_class(expected: str, stats: Dict) -> Tuple[str, float, List[str]]:
    """
    Validates whether the image resembles expected front/side/top capture.
    """
    reasons = []
    aspect = stats.get("aspect", 0.0)
    fill = stats.get("fill_ratio", 0.0)
    bbox_area = stats.get("bbox_area_ratio", 0.0)
    solidity = stats.get("solidity", 0.0)

    if expected == "top":
        # Top view should be more circular/squat, not tall.
        if aspect < 1.85 and bbox_area > 0.04:
            return "top", 0.88, []
        reasons.append("Top image does not look like a top/cap view")
        return "not_top", 0.35, reasons

    # Front/side should be tall bottle-like views.
    tall_score = min(max((aspect - 1.4) / 2.3, 0.0), 1.0)
    fill_score = min(fill / 0.42, 1.0)
    solid_score = min(solidity / 0.75, 1.0)
    confidence = float(np.clip((tall_score * 0.55) + (fill_score * 0.20) + (solid_score * 0.25), 0.0, 1.0))
    if confidence < 0.55:
        reasons.append(f"{expected.capitalize()} image does not look like a tall bottle view")
    return expected if confidence >= 0.55 else f"not_{expected}", confidence, reasons


def _object_class(stats: Dict) -> Tuple[str, float, List[str]]:
    reasons = []
    aspect = stats.get("aspect", 0.0)
    sat = stats.get("median_saturation", 0.0)
    val = stats.get("median_value", 0.0)
    yellow = stats.get("yellow_score", 0.0)
    amber = stats.get("amber_score", 0.0)
    glare = stats.get("glare_score", 0.0)
    solidity = stats.get("solidity", 0.0)

    if not stats.get("mask_found"):
        return "non_bottle_or_unknown", 0.2, ["No dominant object mask found"]

    if aspect < 1.25:
        return "can_or_carton_like", 0.65, ["Object is not tall enough for a normal bottle front/side view"]

    if yellow > 0.32 and sat > 0.38:
        return "yellow_opaque_bottle", 0.86, []

    if amber > 0.25 and sat > 0.24:
        return "amber_glass_bottle", 0.78, []

    if sat < 0.18 and val > 0.45 and (glare > 0.04 or solidity < 0.86):
        return "transparent_bottle", 0.82, []

    if sat >= 0.28:
        return "opaque_bottle", 0.78, []

    return "non_bottle_or_unknown", 0.45, ["Could not confidently determine bottle material/color class"]


def analyze_single_image(path: Optional[str], expected_view: str) -> Dict:
    img = _load(path)
    if img is None:
        return {
            "expected_view": expected_view,
            "capture_ok": False,
            "recapture_required": True,
            "reasons": ["Image not supplied or could not be read"],
            "quality_score": 0.0,
            "view_prediction": "missing",
            "view_confidence": 0.0,
            "object_class": "missing",
            "object_class_confidence": 0.0,
        }

    img = _resize(img)
    stats = _object_stats(img)

    reasons = []
    if not stats["mask_found"]:
        reasons.append("Bottle/object not detected")
    if stats["contour_count"] > 1:
        reasons.append("Multiple significant objects may be present")
    if stats["center_offset"] > 0.22:
        reasons.append("Object is not centered")
    if stats["fill_ratio"] < 0.045:
        reasons.append("Object is too small in frame")
    if stats["brightness"] < 0.18:
        reasons.append("Image is too dark")
    if stats["brightness"] > 0.88:
        reasons.append("Image is too bright")
    if stats["contrast"] < 0.22:
        reasons.append("Image has low contrast")
    if stats["sharpness"] < 55:
        reasons.append("Image may be blurry")
    if stats["glare_score"] > 0.38:
        reasons.append("High glare detected")

    view_pred, view_conf, view_reasons = _view_class(expected_view, stats)
    reasons.extend(view_reasons)

    obj_class, obj_conf, obj_reasons = _object_class(stats)
    reasons.extend(obj_reasons)

    # Quality score
    sharp_score = min(stats["sharpness"] / 260.0, 1.0)
    center_score = 1.0 - min(stats["center_offset"] / 0.35, 1.0)
    brightness_score = 1.0 - min(abs(stats["brightness"] - 0.52) / 0.52, 1.0)
    contrast_score = min(stats["contrast"] / 0.70, 1.0)
    glare_score = 1.0 - min(stats["glare_score"], 1.0)
    mask_score = 1.0 if stats["mask_found"] else 0.0
    quality = float(np.clip(
        sharp_score * 0.22 +
        center_score * 0.18 +
        brightness_score * 0.16 +
        contrast_score * 0.14 +
        glare_score * 0.12 +
        mask_score * 0.18,
        0.0, 1.0
    ))

    capture_ok = quality >= 0.58 and view_conf >= 0.50 and stats["mask_found"] and stats["contour_count"] <= 2
    return {
        "expected_view": expected_view,
        "capture_ok": capture_ok,
        "recapture_required": not capture_ok,
        "reasons": reasons,
        "quality_score": round(quality, 4),
        "view_prediction": view_pred,
        "view_confidence": round(view_conf, 4),
        "object_class": obj_class,
        "object_class_confidence": round(obj_conf, 4),
        "stats": {k: v for k, v in stats.items() if k != "hash"},
        "_hash": stats.get("hash"),
    }


def analyze_capture_set(front_path: Optional[str], side_path: Optional[str], top_path: Optional[str]) -> Dict:
    views = {
        "front": analyze_single_image(front_path, "front"),
        "side": analyze_single_image(side_path, "side"),
        "top": analyze_single_image(top_path, "top"),
    }

    # Duplicate view detection
    duplicates = []
    pairs = [("front", "side"), ("front", "top"), ("side", "top")]
    for a, b in pairs:
        sim = _hash_similarity(views[a].get("_hash"), views[b].get("_hash"))
        if sim >= 0.92:
            duplicates.append({"views": [a, b], "similarity": round(sim, 4), "reason": "Possible duplicate image uploaded in multiple slots"})

    # Object class consistency: front and side should usually agree.
    classes = [views[v]["object_class"] for v in ["front", "side"] if views[v]["object_class"] not in {"missing", "non_bottle_or_unknown"}]
    class_consistent = len(set(classes)) <= 1 if classes else False

    reasons = []
    for v, r in views.items():
        for reason in r.get("reasons", []):
            reasons.append(f"{v}: {reason}")
    for d in duplicates:
        reasons.append(f"{'/'.join(d['views'])}: {d['reason']}")

    recapture = any(v["recapture_required"] for v in views.values()) or bool(duplicates)
    avg_quality = float(np.mean([views[v]["quality_score"] for v in views]))

    result = {
        "capture_ok": not recapture,
        "recapture_required": recapture,
        "average_quality_score": round(avg_quality, 4),
        "views": {k: {kk: vv for kk, vv in v.items() if kk != "_hash"} for k, v in views.items()},
        "duplicate_view_checks": duplicates,
        "object_class_consistent": class_consistent,
        "dominant_object_class": classes[0] if class_consistent and classes else "unknown",
        "reasons": reasons,
    }
    return result


def compare_capture_ai(master_ai: Dict, observed_ai: Dict) -> Dict:
    master_class = (master_ai or {}).get("dominant_object_class") or "unknown"
    observed_class = (observed_ai or {}).get("dominant_object_class") or "unknown"

    enabled = master_class != "unknown" and observed_class != "unknown"
    passed = True
    reasons = []

    if not (observed_ai or {}).get("capture_ok", False):
        passed = False
        reasons.append("Observed capture quality/view validation failed")

    if enabled and master_class != observed_class:
        passed = False
        reasons.append(f"Object class mismatch: registered={master_class}, observed={observed_class}")

    return {
        "enabled": True,
        "passed": passed,
        "master_object_class": master_class,
        "observed_object_class": observed_class,
        "object_class_match": (master_class == observed_class) if enabled else None,
        "observed_capture_ok": (observed_ai or {}).get("capture_ok", False),
        "observed_average_quality_score": (observed_ai or {}).get("average_quality_score"),
        "reasons": reasons,
    }
