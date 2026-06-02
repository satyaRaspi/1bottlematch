
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, Optional

import cv2
import numpy as np

from dl_segmentation import segment_bottle
from runtime_config import enable_overlays, max_image_dim

ASSETS_DIR = Path(__file__).parent / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def _load_image(path: Optional[str]):
    if not path:
        return None
    return cv2.imread(path)


def _largest_contour(mask: np.ndarray):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    return max(contours, key=cv2.contourArea)


def _asset_url(path: Path) -> str:
    rel = path.relative_to(ASSETS_DIR).as_posix()
    return f"/assets/{rel}"


def _draw_overlay(img, mask, view_name: str):
    overlay = img.copy()
    tint = np.zeros_like(img)
    tint[:, :] = (40, 180, 40)
    alpha_mask = (mask > 0).astype(np.uint8)
    overlay = np.where(alpha_mask[..., None] == 1, cv2.addWeighted(overlay, 0.60, tint, 0.40, 0), overlay)

    contour = _largest_contour(mask)
    if contour is not None:
        cv2.drawContours(overlay, [contour], -1, (0, 255, 255), 2)
        x, y, bw, bh = cv2.boundingRect(contour)
        cv2.rectangle(overlay, (x, y), (x + bw, y + bh), (0, 140, 255), 2)
        # Regions
        regions = [
            ('Cap', (x, y, x+bw, y + int(0.15*bh)), (40,40,220)),
            ('Label', (x + int(0.10*bw), y + int(0.32*bh), x + int(0.90*bw), y + int(0.70*bh)), (220,40,40)),
            ('Body', (x + int(0.15*bw), y + int(0.45*bh), x + int(0.85*bw), y + int(0.90*bh)), (255,0,180)),
        ]
        for label, (x0,y0,x1,y1), color in regions:
            cv2.rectangle(overlay, (x0,y0), (x1,y1), color, 2)
            cv2.putText(overlay, label, (x0, max(18, y0-6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
        # Reference lines
        for frac, label in [(0.04, 'Cap W'), (0.10, 'Top'), (0.28, 'Shoulder'), (0.55, 'Mid'), (0.92, 'Base')]:
            yy = y + int(frac * bh)
            cv2.line(overlay, (x, yy), (x+bw, yy), (255,255,255), 1)
            cv2.putText(overlay, label, (x+bw+6, yy+4), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255,255,255), 1, cv2.LINE_AA)

    cv2.putText(overlay, f"View: {view_name}", (14, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2, cv2.LINE_AA)
    return overlay


def create_asset_set(front_path: Optional[str], side_path: Optional[str], top_path: Optional[str], asset_group: str, asset_id: str) -> Dict:
    if not enable_overlays():
        return {"views": {}, "disabled": True, "note": "Overlay generation disabled for faster processing."}

    base = ASSETS_DIR / asset_group / asset_id
    base.mkdir(parents=True, exist_ok=True)

    assets = {"views": {}}
    for view_name, source in [("front", front_path), ("side", side_path), ("top", top_path)]:
        if not source:
            continue
        src = Path(source)
        ext = src.suffix or '.jpg'
        original_out = base / f"{view_name}_original{ext}"
        overlay_out = base / f"{view_name}_overlay.png"
        mask_out = base / f"{view_name}_mask.png"
        shutil.copy2(src, original_out)

        img = _load_image(str(src))
        if img is None:
            continue
        h, w = img.shape[:2]
        md = max_image_dim()
        if max(h, w) > md:
            scale = md / max(h, w)
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        mask, meta = segment_bottle(img)
        cv2.imwrite(str(mask_out), mask)
        overlay = _draw_overlay(img, mask, view_name.capitalize())
        cv2.imwrite(str(overlay_out), overlay)

        assets["views"][view_name] = {
            "original_url": _asset_url(original_out),
            "overlay_url": _asset_url(overlay_out),
            "mask_url": _asset_url(mask_out),
            "segmentation_mode": meta.get('mode'),
            "onnx_used": bool(meta.get('onnx_used')),
            "segmentation_quality": meta.get('dl_mask_quality_score'),
        }
    return assets
