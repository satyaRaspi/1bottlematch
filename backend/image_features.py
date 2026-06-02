
"""
Image-derived Bottle Feature Extraction
Version: 1.5.7

This module deliberately avoids pure image matching. It extracts measurable,
repeatable physical proxies from front/side/top images and converts them into
a physical signature vector.

For production, replace pixel proxies with calibrated mm measurements using
camera calibration, reference markers, depth sensors, and controlled lighting.
"""

from __future__ import annotations

import math
import hashlib
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
from ml_features import extract_ml_features
from dl_segmentation import segmentation_features_from_image
from runtime_config import max_image_dim


def _safe_float(v, default=0.0) -> float:
    try:
        if v is None:
            return default
        if isinstance(v, str) and not v.strip():
            return default
        return float(v)
    except Exception:
        return default


def stable_numeric_hash(value: str, modulo: int = 10_000_000) -> float:
    if not value:
        return 0.0
    h = hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()
    return float(int(h[:12], 16) % modulo)


def _load_image(path: str) -> Optional[np.ndarray]:
    if not path:
        return None
    img = cv2.imread(path)
    return img


def _largest_contour(mask: np.ndarray):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    return max(contours, key=cv2.contourArea)


def _dominant_color(img: np.ndarray, mask: Optional[np.ndarray] = None) -> Tuple[float, float, float]:
    if img is None or img.size == 0:
        return 0.0, 0.0, 0.0
    if mask is not None:
        pts = img[mask > 0]
        if pts.size == 0:
            return 0.0, 0.0, 0.0
    else:
        pts = img.reshape((-1, 3))
    # OpenCV is BGR; convert to RGB order
    med = np.median(pts, axis=0)
    b, g, r = [float(x) for x in med[:3]]
    return r, g, b


def _color_stats(img: np.ndarray, mask: Optional[np.ndarray] = None) -> Tuple[float, float, float]:
    if img is None or img.size == 0:
        return 0.0, 0.0, 0.0
    if mask is not None:
        pts = img[mask > 0]
        if pts.size == 0:
            pts = img.reshape((-1, 3))
    else:
        pts = img.reshape((-1, 3))
    if pts.size == 0:
        return 0.0, 0.0, 0.0
    hsv = cv2.cvtColor(pts.reshape((-1, 1, 3)).astype("uint8"), cv2.COLOR_BGR2HSV).reshape((-1, 3))
    sat = float(np.median(hsv[:, 1]) / 255.0)
    val = float(np.median(hsv[:, 2]) / 255.0)
    # colorfulness proxy from RGB channel spread
    rgb = pts[:, [2, 1, 0]].astype("float32")
    spread = float(np.mean(np.std(rgb, axis=1)) / 255.0)
    return sat, val, spread


def _edge_density(gray: np.ndarray) -> float:
    if gray is None or gray.size == 0:
        return 0.0
    edges = cv2.Canny(gray, 80, 180)
    return float(np.mean(edges > 0))


def _region(img: np.ndarray, x0, y0, x1, y1) -> np.ndarray:
    h, w = img.shape[:2]
    x0, x1 = max(0, int(x0)), min(w, int(x1))
    y0, y1 = max(0, int(y0)), min(h, int(y1))
    if x1 <= x0 or y1 <= y0:
        return img[0:0, 0:0]
    return img[y0:y1, x0:x1]


def _width_at_y(mask: np.ndarray, y: int) -> float:
    h, w = mask.shape[:2]
    y = max(0, min(h - 1, int(y)))
    xs = np.where(mask[y] > 0)[0]
    if len(xs) < 2:
        return 0.0
    return float(xs.max() - xs.min() + 1)


def extract_view_features(path: str, prefix: str = "") -> Dict[str, float]:
    img = _load_image(path)
    if img is None:
        return {}

    original_h, original_w = img.shape[:2]
    max_dim = max_image_dim()
    scale = 1.0
    if max(original_h, original_w) > max_dim:
        scale = max_dim / max(original_h, original_w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Light-DL-assisted segmentation.
    # If ONNX model is configured, it is used; otherwise OpenCV GrabCut fallback is used.
    mask, dl_features = segmentation_features_from_image(img, prefix=prefix)
    contour = _largest_contour(mask)

    if contour is None or cv2.contourArea(contour) < 100:
        return {}

    x, y, bw, bh = cv2.boundingRect(contour)
    contour_mask = np.zeros(mask.shape, dtype=np.uint8)
    cv2.drawContours(contour_mask, [contour], -1, 255, -1)

    area = float(cv2.contourArea(contour))
    rect_area = float(max(bw * bh, 1))
    hull = cv2.convexHull(contour)
    hull_area = float(max(cv2.contourArea(hull), 1.0))
    perimeter = float(cv2.arcLength(contour, True))

    # Extract widths at normalized heights
    top_width = _width_at_y(contour_mask, y + 0.10 * bh)
    cap_width = _width_at_y(contour_mask, y + 0.04 * bh)
    shoulder_width = _width_at_y(contour_mask, y + 0.28 * bh)
    mid_width = _width_at_y(contour_mask, y + 0.55 * bh)
    bottom_width = _width_at_y(contour_mask, y + 0.92 * bh)

    # Symmetry proxy: compare left and right halves in bbox
    roi_mask = contour_mask[y:y+bh, x:x+bw]
    half = bw // 2
    if half > 1:
        left = roi_mask[:, :half]
        right = cv2.flip(roi_mask[:, bw-half:bw], 1)
        symmetry = 1.0 - float(np.mean(np.abs(left.astype("float32") - right.astype("float32"))) / 255.0)
    else:
        symmetry = 0.0

    # Approx regions
    cap_region = _region(img, x, y, x + bw, y + 0.15 * bh)
    label_region = _region(img, x + 0.10 * bw, y + 0.32 * bh, x + 0.90 * bw, y + 0.70 * bh)
    glass_region = _region(img, x + 0.10 * bw, y + 0.72 * bh, x + 0.90 * bw, y + 0.93 * bh)
    body_region = _region(img, x + 0.15 * bw, y + 0.45 * bh, x + 0.85 * bw, y + 0.90 * bh)

    cr, cg, cb = _dominant_color(cap_region)
    lr, lg, lb = _dominant_color(label_region)
    gr, gg, gb = _dominant_color(glass_region)
    br, bg, bb = _dominant_color(body_region)

    label_gray = cv2.cvtColor(label_region, cv2.COLOR_BGR2GRAY) if label_region.size else gray[0:0, 0:0]
    glass_gray = cv2.cvtColor(glass_region, cv2.COLOR_BGR2GRAY) if glass_region.size else gray[0:0, 0:0]

    edge_density_label = _edge_density(label_gray)
    edge_density_body = _edge_density(glass_gray)

    # Barcode-ish score: many vertical edges in right label segment
    barcode_region = _region(label_gray, label_gray.shape[1] * 0.55 if label_gray.size else 0, 0,
                             label_gray.shape[1] if label_gray.size else 0, label_gray.shape[0] if label_gray.size else 0)
    barcode_score = _edge_density(barcode_region) * 1.4 if barcode_region.size else 0.0

    brightness = gray[contour_mask > 0]
    transparency = float(np.std(brightness) / 255.0) if brightness.size else 0.0
    reflection = float(np.mean(brightness > 235)) if brightness.size else 0.0

    # Shoulder slope proxies using width differences
    shoulder_left_slope = abs((shoulder_width - top_width) / max(bh, 1))
    shoulder_right_slope = shoulder_left_slope

    # Detect likely label band from horizontal/vertical edge concentration.
    # This replaces earlier fixed constants that made unlike objects look similar.
    label_top_ratio = 0.0
    label_height_ratio = 0.0
    label_width_ratio = 0.0
    if bw > 5 and bh > 5:
        bbox_gray = gray[y:y+bh, x:x+bw]
        bbox_edges = cv2.Canny(bbox_gray, 60, 160)
        row_density = np.mean(bbox_edges > 0, axis=1)
        threshold = max(float(np.mean(row_density) + np.std(row_density) * 0.65), 0.035)
        rows = np.where(row_density > threshold)[0]
        if len(rows) >= max(4, int(0.08 * bh)):
            y0, y1 = int(rows.min()), int(rows.max())
            label_top_ratio = float(y0 / max(bh, 1))
            label_height_ratio = float((y1 - y0 + 1) / max(bh, 1))
            # approximate label width from edge presence in detected rows
            band = bbox_edges[y0:y1+1, :]
            col_density = np.mean(band > 0, axis=0) if band.size else np.array([])
            cols = np.where(col_density > max(float(np.mean(col_density) + np.std(col_density) * 0.45), 0.025))[0] if col_density.size else []
            label_width_ratio = float((cols.max() - cols.min() + 1) / max(bw, 1)) if len(cols) >= 3 else 0.0

    body_sat, body_val, body_colorfulness = _color_stats(body_region)
    glass_sat, glass_val, glass_colorfulness = _color_stats(glass_region)
    cap_sat, cap_val, cap_colorfulness = _color_stats(cap_region)
    contour_sat, contour_val, contour_colorfulness = _color_stats(img, contour_mask)

    # Object appearance class proxies.
    # Transparent plastic/glass usually has low saturation and higher internal texture/reflection.
    # Painted/opaque bottles usually have higher saturation and less internal transparency.
    opaque_surface_score = float(np.clip((body_sat * 0.55) + (body_colorfulness * 0.30) + ((1.0 - transparency) * 0.15), 0.0, 1.0))
    transparent_surface_score = float(np.clip((transparency * 0.50) + ((1.0 - body_sat) * 0.30) + (reflection * 0.20), 0.0, 1.0))
    yellow_dominance_score = float(np.clip(((br - bb) / 255.0 + (bg - bb) / 255.0) / 2.0, 0.0, 1.0))
    dark_cap_score = float(np.clip((1.0 - cap_val) * 0.75 + (cap_sat * 0.25), 0.0, 1.0))

    # Pixel values scaled back approximately to original pixels
    inv_scale = 1.0 / scale if scale else 1.0

    features_out = {
        f"{prefix}height_px": float(bh * inv_scale),
        f"{prefix}width_px": float(bw * inv_scale),
        f"{prefix}aspect_ratio": float(bh / max(bw, 1)),
        f"{prefix}area_ratio": float(area / max(w * h, 1)),
        f"{prefix}contour_extent": float(area / rect_area),
        f"{prefix}solidity": float(area / hull_area),
        f"{prefix}perimeter_norm": float(perimeter / max((bw + bh), 1)),
        f"{prefix}top_width_ratio": float(top_width / max(bw, 1)),
        f"{prefix}mid_width_ratio": float(mid_width / max(bw, 1)),
        f"{prefix}bottom_width_ratio": float(bottom_width / max(bw, 1)),
        f"{prefix}shoulder_left_slope": float(shoulder_left_slope),
        f"{prefix}shoulder_right_slope": float(shoulder_right_slope),
        f"{prefix}symmetry_score": float(symmetry),
        f"{prefix}neck_height_ratio": float(max(0.01, min(0.45, 0.28 if shoulder_width <= 0 else abs(shoulder_width - top_width) / max(shoulder_width, 1)))),
        f"{prefix}shoulder_height_ratio": float(0.28),
        f"{prefix}cap_width_ratio": float(cap_width / max(bw, 1)),
        f"{prefix}cap_height_ratio": float(max(0.03, min(0.22, 0.15 if cap_width > top_width * 1.2 else 0.08))),
        f"{prefix}seal_band_ratio": 0.07,
        f"{prefix}closure_color_r": cr,
        f"{prefix}closure_color_g": cg,
        f"{prefix}closure_color_b": cb,
        f"{prefix}front_label_top_ratio": float(label_top_ratio),
        f"{prefix}front_label_height_ratio": float(label_height_ratio),
        f"{prefix}front_label_width_ratio": float(label_width_ratio),
        f"{prefix}label_color_r": lr,
        f"{prefix}label_color_g": lg,
        f"{prefix}label_color_b": lb,
        f"{prefix}label_edge_density": float(edge_density_label),
        f"{prefix}barcode_region_score": float(min(barcode_score, 1.0)),
        f"{prefix}excise_mark_region_score": float(edge_density_label * 0.8),
        f"{prefix}logo_region_density": float(edge_density_label * 0.6),
        f"{prefix}glass_color_r": gr,
        f"{prefix}glass_color_g": gg,
        f"{prefix}glass_color_b": gb,
        f"{prefix}transparency_score": float(transparency),
        f"{prefix}reflection_score": float(reflection),
        f"{prefix}surface_texture_score": float(edge_density_body),
        f"{prefix}liquid_color_r": br,
        f"{prefix}liquid_color_g": bg,
        f"{prefix}liquid_color_b": bb,
        f"{prefix}fill_level_ratio": 0.88,
        f"{prefix}base_width_ratio": float(bottom_width / max(bw, 1)),
        f"{prefix}punt_depth_proxy": 0.0,
        f"{prefix}bottom_ring_score": float(edge_density_body),
        f"{prefix}opaque_surface_score": float(opaque_surface_score),
        f"{prefix}transparent_surface_score": float(transparent_surface_score),
        f"{prefix}yellow_dominance_score": float(yellow_dominance_score),
        f"{prefix}dark_cap_score": float(dark_cap_score),
        f"{prefix}body_saturation_score": float(body_sat),
        f"{prefix}contour_saturation_score": float(contour_sat),
        f"{prefix}top_circularity": 0.0,
    }
    features_out.update(dl_features)
    return features_out


def merge_views(front_path: Optional[str], side_path: Optional[str], top_path: Optional[str]) -> Dict[str, float]:
    """
    Generate a single signature map from front/side/top views.

    Front view drives most canonical keys. Side view is used to improve depth and
    profile fields. Top view improves cap/top circularity fields.
    """
    result: Dict[str, float] = {}

    front = extract_view_features(front_path or "", prefix="")
    side = extract_view_features(side_path or "", prefix="side_")
    top = extract_view_features(top_path or "", prefix="top_")

    result.update(front)

    if side:
        # Derive depth and profile proxies from side view.
        result["depth_px"] = side.get("side_width_px", 0.0)
        result["side_aspect_ratio"] = side.get("side_aspect_ratio", 0.0)
        result["side_contour_extent"] = side.get("side_contour_extent", 0.0)
        result["side_shoulder_height_ratio"] = side.get("side_shoulder_height_ratio", 0.0)
        # Use side colors when front is label-heavy.
        result["side_glass_color_r"] = side.get("side_glass_color_r", 0.0)
        result["side_glass_color_g"] = side.get("side_glass_color_g", 0.0)
        result["side_glass_color_b"] = side.get("side_glass_color_b", 0.0)

    if top:
        tw = top.get("top_width_px", 0.0)
        th = top.get("top_height_px", 0.0)
        if tw and th:
            result["top_circularity"] = min(tw, th) / max(tw, th)
            result["cap_width_ratio"] = result.get("cap_width_ratio", result["top_circularity"])
            result["bottom_ring_score"] = top.get("top_label_edge_density", result.get("bottom_ring_score", 0.0))

    return {k: float(v) for k, v in result.items() if isinstance(v, (int, float)) and not math.isnan(float(v))}


def build_signature(front_path: Optional[str], side_path: Optional[str], top_path: Optional[str], manual: Dict[str, object]) -> Dict[str, float]:
    signature = merge_views(front_path, side_path, top_path)

    # ML-assisted feature extraction is additive. The deterministic physical
    # signature remains the source of truth, while ML features add better
    # segmentation, color clusters, texture, gradients and quality signals.
    try:
        ml = extract_ml_features(front_path, side_path, top_path)
        signature.update(ml)
        signature["ml_assisted_enabled"] = 1.0
    except Exception:
        signature["ml_assisted_enabled"] = 0.0

    # Manual/calibrated values override or augment image proxies.
    numeric_manual_fields = [
        "weight_g", "height_mm", "width_mm", "depth_mm", "neck_diameter_mm",
        "cap_height_mm", "label_top_offset_mm", "label_width_mm",
        "label_height_mm", "liquid_volume_ml"
    ]
    for field in numeric_manual_fields:
        if field in manual and manual[field] not in (None, ""):
            signature[field] = _safe_float(manual[field])

    if manual.get("sku_code"):
        signature["sku_code_numeric"] = stable_numeric_hash(str(manual.get("sku_code")))
    if manual.get("barcode"):
        signature["barcode_numeric_hash"] = stable_numeric_hash(str(manual.get("barcode")))

    return signature
