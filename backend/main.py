
from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from database import init_db, insert_bottle, update_bottle_assets, update_bottle_capture_ai, list_bottles, get_bottle, delete_bottle, insert_log, list_logs, clear_logs, insert_processing_match, list_processing_matches, get_processing_match
from image_features import build_signature
from matcher import find_best_match, compare_signatures
from signature_schema import PARAMETERS, default_tolerances, default_weights
from dl_segmentation import status as dl_segmentation_status
from overlay_visualization import ASSETS_DIR, create_asset_set
from runtime_config import config_payload, detailed_parameter_trace
from ai_quality import analyze_capture_set, compare_capture_ai

APP_VERSION = "1.6.0"

app = FastAPI(
    title="Bottle Signature Core API",
    description="Physical signature generation and matching API for bottle identification.",
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


async def _save_upload(upload: Optional[UploadFile], folder: Path, name: str) -> Optional[str]:
    if upload is None:
        return None
    suffix = Path(upload.filename or name).suffix or ".jpg"
    path = folder / f"{name}{suffix}"
    content = await upload.read()
    if not content:
        return None
    path.write_bytes(content)
    return str(path)


def _manual_dict(**kwargs):
    return {k: _blank_to_none(v) for k, v in kwargs.items() if _blank_to_none(v) is not None}


def _blank_to_none(value):
    if value == "":
        return None
    return value


def _truthy(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "checked"}


def _demo_capture_ai(kind: str):
    class_map = {
        "clear_soda": "transparent_bottle",
        "yellow_flask": "yellow_opaque_bottle",
        "amber_liquor": "amber_glass_bottle",
    }
    return {
        "capture_ok": True,
        "recapture_required": False,
        "average_quality_score": 0.86,
        "views": {},
        "duplicate_view_checks": [],
        "object_class_consistent": True,
        "dominant_object_class": class_map.get(kind, "unknown"),
        "reasons": [],
    }


def _demo_signature(kind: str):
    """
    Demo signatures are synthetic but intentionally separated so the strict
    mismatch gates can demonstrate MATCH / NO_MATCH behavior without image upload.
    """
    base = {
        "height_px": 640.0,
        "width_px": 165.0,
        "aspect_ratio": 3.88,
        "area_ratio": 0.22,
        "contour_extent": 0.72,
        "solidity": 0.82,
        "perimeter_norm": 2.4,
        "top_width_ratio": 0.34,
        "mid_width_ratio": 0.90,
        "bottom_width_ratio": 0.86,
        "shoulder_left_slope": 0.18,
        "shoulder_right_slope": 0.18,
        "symmetry_score": 0.86,
        "neck_height_ratio": 0.22,
        "shoulder_height_ratio": 0.28,
        "cap_width_ratio": 0.42,
        "cap_height_ratio": 0.08,
        "seal_band_ratio": 0.07,
        "front_label_top_ratio": 0.32,
        "front_label_height_ratio": 0.28,
        "front_label_width_ratio": 0.82,
        "label_edge_density": 0.08,
        "barcode_region_score": 0.08,
        "excise_mark_region_score": 0.05,
        "logo_region_density": 0.06,
        "transparency_score": 0.25,
        "reflection_score": 0.04,
        "surface_texture_score": 0.05,
        "fill_level_ratio": 0.88,
        "base_width_ratio": 0.86,
        "punt_depth_proxy": 0.0,
        "bottom_ring_score": 0.04,
        "top_circularity": 0.82,
        "dl_mask_quality_score": 0.86,
        "dl_mask_bbox_w": 165.0,
        "dl_mask_bbox_h": 640.0,
        "dl_mask_fill_ratio": 0.24,
        "dl_mask_contour_area": 76000.0,
        "ml_capture_quality_score": 0.82,
        "ml_assisted_enabled": 1.0,
    }

    if kind == "clear_soda":
        base.update({
            "closure_color_r": 36, "closure_color_g": 35, "closure_color_b": 38,
            "label_color_r": 35, "label_color_g": 34, "label_color_b": 30,
            "glass_color_r": 184, "glass_color_g": 188, "glass_color_b": 182,
            "liquid_color_r": 175, "liquid_color_g": 170, "liquid_color_b": 150,
            "opaque_surface_score": 0.18,
            "transparent_surface_score": 0.72,
            "yellow_dominance_score": 0.04,
            "body_saturation_score": 0.10,
            "contour_saturation_score": 0.12,
        })
    elif kind == "yellow_flask":
        base.update({
            "height_px": 690.0, "width_px": 190.0, "aspect_ratio": 3.63,
            "closure_color_r": 20, "closure_color_g": 20, "closure_color_b": 22,
            "label_color_r": 235, "label_color_g": 218, "label_color_b": 52,
            "glass_color_r": 240, "glass_color_g": 224, "glass_color_b": 48,
            "liquid_color_r": 240, "liquid_color_g": 220, "liquid_color_b": 40,
            "opaque_surface_score": 0.86,
            "transparent_surface_score": 0.14,
            "yellow_dominance_score": 0.82,
            "body_saturation_score": 0.78,
            "contour_saturation_score": 0.76,
            "front_label_top_ratio": 0.58,
            "front_label_height_ratio": 0.18,
            "front_label_width_ratio": 0.42,
        })
    elif kind == "amber_liquor":
        base.update({
            "height_px": 610.0, "width_px": 178.0, "aspect_ratio": 3.43,
            "closure_color_r": 82, "closure_color_g": 62, "closure_color_b": 35,
            "label_color_r": 220, "label_color_g": 195, "label_color_b": 130,
            "glass_color_r": 150, "glass_color_g": 96, "glass_color_b": 38,
            "liquid_color_r": 175, "liquid_color_g": 98, "liquid_color_b": 28,
            "opaque_surface_score": 0.34,
            "transparent_surface_score": 0.52,
            "yellow_dominance_score": 0.30,
            "body_saturation_score": 0.38,
            "contour_saturation_score": 0.35,
            "front_label_top_ratio": 0.36,
            "front_label_height_ratio": 0.30,
            "front_label_width_ratio": 0.76,
        })
    return {k: float(v) for k, v in base.items()}



@app.get("/")
def health():
    return {
        "service": "Bottle Signature Core API",
        "version": APP_VERSION,
        "status": "running",
        "capabilities": [
            "build physical bottle signature",
            "register bottle/SKU",
            "identify bottle from captured signature",
            "tolerance-based weighted matching",
            "ML-assisted feature extraction",
            "K-means color clustering",
            "ORB/texture/gradient profile extraction",
            "ML-assisted similarity gate",
            "Light DL segmentation with optional ONNX Runtime",
            "OpenCV GrabCut fallback segmentation",
            "Image overlay visualization",
            "Master/observed overlay asset generation",
            "Real model segmentation via ultralytics or ONNX",
            "Real-time processing status trace",
            "Preliminary physical characteristics gate",
            "Detailed per-check scrolling processing trace",
            "Distinctive object appearance hard gate",
            "Create demo registered bottle data",
            "AI capture quality assistant",
            "AI front/side/top view validation",
            "AI object class detection",
            "Fast processing mode with optional overlays/real-DL toggles"
        ],
        "architecture": "physical_signature_engine_plus_overlay_visualization_plus_real_time_status_plus_preliminary_physical_gate",
    }


@app.get("/dl/status")
def dl_status():
    return dl_segmentation_status()



@app.get("/runtime/config")
def runtime_config():
    return config_payload()


@app.get("/ml/status")
def ml_status():
    return {"enabled": True, "version": APP_VERSION, "mode": "Physical signature engine + ML-assisted feature extraction", "ml_assisted_methods": ["K-means dominant color clustering", "ORB keypoint density", "Laplacian texture complexity", "Gradient histogram profile", "Cross-view consistency scoring", "ML-assisted feature vector similarity"], "note": "ML assists feature extraction and similarity scoring. It does not replace the physical signature engine."}


@app.get("/parameters")
def get_parameters():
    return {
        "count": len(PARAMETERS),
        "parameters": [
            {
                "key": p.key,
                "label": p.label,
                "category": p.category,
                "unit": p.unit,
                "default_weight": p.default_weight,
                "default_tolerance": p.default_tolerance,
                "description": p.description,
            }
            for p in PARAMETERS
        ],
    }


@app.get("/logs")
def get_logs(limit: int = 200):
    return {
        "count": len(list_logs(limit)),
        "logs": list_logs(limit),
    }


@app.delete("/logs")
def delete_logs():
    deleted = clear_logs()
    insert_log("LOGS_CLEARED", "SUCCESS", f"Cleared {deleted} logs")
    return {"message": "Logs cleared", "deleted": deleted}


@app.get("/processing-matches")
def get_processing_matches(limit: int = 200):
    items = list_processing_matches(limit)
    return {
        "count": len(items),
        "processing_matches": items,
    }


@app.get("/processing-matches/{processing_match_id}")
def processing_match_detail(processing_match_id: str):
    item = get_processing_match(processing_match_id)
    if not item:
        raise HTTPException(status_code=404, detail="Processing bottle match record not found")
    return item






@app.post("/signature/capture-ai-preview")
async def capture_ai_preview(
    front_image: Optional[UploadFile] = File(None),
    side_image: Optional[UploadFile] = File(None),
    top_image: Optional[UploadFile] = File(None),
):
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        front = await _save_upload(front_image, folder, "front")
        side = await _save_upload(side_image, folder, "side")
        top = await _save_upload(top_image, folder, "top")

        if not (front and side and top):
            raise HTTPException(status_code=400, detail="Upload all three images for AI capture/view validation.")

        capture_ai = analyze_capture_set(front, side, top)

    insert_log(
        "CAPTURE_AI_PREVIEW",
        "SUCCESS" if capture_ai.get("capture_ok") else "RECAPTURE_REQUIRED",
        "AI capture quality and view validation completed",
        request={"front_image": bool(front), "side_image": bool(side), "top_image": bool(top)},
        response={
            "capture_ok": capture_ai.get("capture_ok"),
            "average_quality_score": capture_ai.get("average_quality_score"),
            "dominant_object_class": capture_ai.get("dominant_object_class"),
            "reasons": capture_ai.get("reasons"),
        },
    )
    return capture_ai


@app.post("/signature/build")
async def build_signature_preview(
    front_image: Optional[UploadFile] = File(None),
    side_image: Optional[UploadFile] = File(None),
    top_image: Optional[UploadFile] = File(None),
    weight_g: Optional[str] = Form(None),
    height_mm: Optional[str] = Form(None),
    width_mm: Optional[str] = Form(None),
    depth_mm: Optional[str] = Form(None),
    neck_diameter_mm: Optional[str] = Form(None),
    cap_height_mm: Optional[str] = Form(None),
    label_top_offset_mm: Optional[str] = Form(None),
    label_width_mm: Optional[str] = Form(None),
    label_height_mm: Optional[str] = Form(None),
    liquid_volume_ml: Optional[str] = Form(None),
    sku_code: Optional[str] = Form(None),
    barcode: Optional[str] = Form(None),
):
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        front = await _save_upload(front_image, folder, "front")
        side = await _save_upload(side_image, folder, "side")
        top = await _save_upload(top_image, folder, "top")

        observed_capture_ai = analyze_capture_set(front, side, top)

        manual = _manual_dict(
            weight_g=weight_g,
            height_mm=height_mm,
            width_mm=width_mm,
            depth_mm=depth_mm,
            neck_diameter_mm=neck_diameter_mm,
            cap_height_mm=cap_height_mm,
            label_top_offset_mm=label_top_offset_mm,
            label_width_mm=label_width_mm,
            label_height_mm=label_height_mm,
            liquid_volume_ml=liquid_volume_ml,
            sku_code=sku_code,
            barcode=barcode,
        )

        signature = build_signature(front, side, top, manual)

    return {
        "signature_parameter_count": len(signature),
        "signature": signature,
        "note": "Core registration and identification require 3-axis photos. Optional physical measurements are not required. For production, use calibrated cameras/depth sensors/reference markers to convert pixel proxies into physical measurements."
    }


@app.post("/bottles/register")
async def register_bottle(
    brand: str = Form(...),
    product_name: str = Form(...),
    sku_code: Optional[str] = Form(None),
    quantity_ml: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    barcode: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    front_image: Optional[UploadFile] = File(None),
    side_image: Optional[UploadFile] = File(None),
    top_image: Optional[UploadFile] = File(None),
    weight_g: Optional[str] = Form(None),
    height_mm: Optional[str] = Form(None),
    width_mm: Optional[str] = Form(None),
    depth_mm: Optional[str] = Form(None),
    neck_diameter_mm: Optional[str] = Form(None),
    cap_height_mm: Optional[str] = Form(None),
    label_top_offset_mm: Optional[str] = Form(None),
    label_width_mm: Optional[str] = Form(None),
    label_height_mm: Optional[str] = Form(None),
):
    if not (front_image and side_image and top_image):
        raise HTTPException(status_code=400, detail="Upload all three required 3-axis photos: front image, side image, and top image. Optional physical measurements are not required.")

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        front = await _save_upload(front_image, folder, "front")
        side = await _save_upload(side_image, folder, "side")
        top = await _save_upload(top_image, folder, "top")

        observed_capture_ai = analyze_capture_set(front, side, top)

        manual = _manual_dict(
            weight_g=weight_g,
            height_mm=height_mm,
            width_mm=width_mm,
            depth_mm=depth_mm,
            neck_diameter_mm=neck_diameter_mm,
            cap_height_mm=cap_height_mm,
            label_top_offset_mm=label_top_offset_mm,
            label_width_mm=label_width_mm,
            label_height_mm=label_height_mm,
            liquid_volume_ml=quantity_ml,
            sku_code=sku_code,
            barcode=barcode,
        )

        capture_ai = analyze_capture_set(front, side, top)
        signature = build_signature(front, side, top, manual)

        if len(signature) < 8:
            raise HTTPException(status_code=400, detail="Could not build enough signature parameters from the uploaded 3-axis photos. Upload clearer front, side, and top images.")

        bottle_id = insert_bottle({
            "brand": brand,
            "product_name": product_name,
            "sku_code": sku_code,
            "quantity_ml": float(quantity_ml) if quantity_ml not in (None, "") else None,
            "color": color,
            "barcode": barcode,
            "notes": notes,
            "signature": signature,
            "tolerances": default_tolerances(),
            "weights": default_weights(),
            "image_assets": {},
            "capture_ai": capture_ai,
        })
        image_assets = create_asset_set(front, side, top, "bottles", str(bottle_id))
        update_bottle_assets(bottle_id, image_assets)
        update_bottle_capture_ai(bottle_id, capture_ai)

    response = {
        "id": bottle_id,
        "message": "Bottle signature registered successfully",
        "signature_parameter_count": len(signature),
        "signature": signature,
        "image_assets": image_assets,
        "capture_ai": capture_ai,
    }
    insert_log(
        "REGISTER_BOTTLE",
        "SUCCESS",
        f"Registered bottle signature for {brand} - {product_name}",
        request={
            "brand": brand,
            "product_name": product_name,
            "sku_code": sku_code,
            "quantity_ml": quantity_ml,
            "color": color,
            "barcode": barcode,
            "front_image": bool(front),
            "side_image": bool(side),
            "top_image": bool(top),
        },
        response=response,
    )
    return response


def _safe_bottle_summary(b):
    return {
        "id": b.get("id"),
        "brand": b.get("brand") or "",
        "product_name": b.get("product_name") or "",
        "sku_code": b.get("sku_code") or "",
        "quantity_ml": b.get("quantity_ml"),
        "color": b.get("color") or "",
        "barcode": b.get("barcode") or "",
        "signature_parameter_count": len(b.get("signature") or {}),
        "image_assets": b.get("image_assets") or {},
        "capture_ai": b.get("capture_ai") or {},
        "object_class": ((b.get("capture_ai") or {}).get("dominant_object_class") or "unknown"),
        "capture_quality": ((b.get("capture_ai") or {}).get("average_quality_score") or None),
        "created_at": b.get("created_at") or "",
    }




@app.post("/demo/create")
def create_demo_data():
    existing = list_bottles()
    demo_marker = "DEMO-DATA"
    existing_skus = {b.get("sku_code") for b in existing}

    demo_items = [
        {
            "brand": "Demo Kinley",
            "product_name": "Clear Strong Soda Bottle",
            "sku_code": "DEMO-KINLEY-SODA-750",
            "quantity_ml": 750,
            "color": "Clear / black / yellow label",
            "barcode": "890000000001",
            "notes": demo_marker,
            "signature": _demo_signature("clear_soda"),
            "capture_ai": _demo_capture_ai("clear_soda"),
        },
        {
            "brand": "Demo Cello",
            "product_name": "Yellow Opaque Flask Bottle",
            "sku_code": "DEMO-CELLO-YELLOW-900",
            "quantity_ml": 900,
            "color": "Opaque yellow / black cap",
            "barcode": "890000000002",
            "notes": demo_marker,
            "signature": _demo_signature("yellow_flask"),
            "capture_ai": _demo_capture_ai("yellow_flask"),
        },
        {
            "brand": "Demo Amber",
            "product_name": "Amber Liquor Style Bottle",
            "sku_code": "DEMO-AMBER-LIQUOR-750",
            "quantity_ml": 750,
            "color": "Amber / cream label",
            "barcode": "890000000003",
            "notes": demo_marker,
            "signature": _demo_signature("amber_liquor"),
            "capture_ai": _demo_capture_ai("amber_liquor"),
        },
    ]

    created = []
    skipped = []
    for item in demo_items:
        if item["sku_code"] in existing_skus:
            skipped.append(item["sku_code"])
            continue
        bottle_id = insert_bottle({
            "brand": item["brand"],
            "product_name": item["product_name"],
            "sku_code": item["sku_code"],
            "quantity_ml": item["quantity_ml"],
            "color": item["color"],
            "barcode": item["barcode"],
            "notes": item["notes"],
            "signature": item["signature"],
            "tolerances": default_tolerances(),
            "weights": default_weights(),
            "image_assets": {},
            "capture_ai": item.get("capture_ai", {}),
        })
        created.append({"id": bottle_id, "sku_code": item["sku_code"], "brand": item["brand"], "product_name": item["product_name"]})

    insert_log(
        "CREATE_DEMO_DATA",
        "SUCCESS",
        f"Created {len(created)} demo bottle records, skipped {len(skipped)} existing records",
        request={"demo_items": [i["sku_code"] for i in demo_items]},
        response={"created": created, "skipped": skipped},
    )

    return {
        "message": "Demo data created",
        "created_count": len(created),
        "skipped_count": len(skipped),
        "created": created,
        "skipped": skipped,
        "note": "Demo records are synthetic signatures for testing dropdown, matching gates and no-match behavior."
    }


@app.get("/bottles")
def bottles():
    try:
        items = list_bottles()
        response_items = [_safe_bottle_summary(b) for b in items]
        insert_log("LIST_BOTTLES", "SUCCESS", f"Listed {len(response_items)} bottle signatures")
        return {
            "count": len(response_items),
            "bottles": response_items,
        }
    except Exception as exc:
        insert_log("LIST_BOTTLES", "ERROR", f"Could not list bottle signatures: {exc}")
        raise HTTPException(status_code=500, detail=f"Could not list bottle signatures: {exc}")


@app.get("/bottles/{bottle_id}")
def bottle_detail(bottle_id: int):
    item = get_bottle(bottle_id)
    if not item:
        raise HTTPException(status_code=404, detail="Bottle not found")
    return item


@app.delete("/bottles/{bottle_id}")
def bottle_delete(bottle_id: int):
    ok = delete_bottle(bottle_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Bottle not found")
    insert_log("DELETE_BOTTLE", "SUCCESS", f"Deleted bottle id {bottle_id}", request={"bottle_id": bottle_id})
    return {"message": "Bottle deleted"}


@app.post("/identify")
async def identify_bottle(
    front_image: Optional[UploadFile] = File(None),
    side_image: Optional[UploadFile] = File(None),
    top_image: Optional[UploadFile] = File(None),
    weight_g: Optional[str] = Form(None),
    height_mm: Optional[str] = Form(None),
    width_mm: Optional[str] = Form(None),
    depth_mm: Optional[str] = Form(None),
    neck_diameter_mm: Optional[str] = Form(None),
    cap_height_mm: Optional[str] = Form(None),
    label_top_offset_mm: Optional[str] = Form(None),
    label_width_mm: Optional[str] = Form(None),
    label_height_mm: Optional[str] = Form(None),
    liquid_volume_ml: Optional[str] = Form(None),
    sku_code: Optional[str] = Form(None),
    barcode: Optional[str] = Form(None),
):
    candidates = list_bottles()
    if not candidates:
        raise HTTPException(status_code=400, detail="No registered bottle signatures found. Register at least one bottle first.")

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        front = await _save_upload(front_image, folder, "front")
        side = await _save_upload(side_image, folder, "side")
        top = await _save_upload(top_image, folder, "top")

        observed_capture_ai = analyze_capture_set(front, side, top)

        manual = _manual_dict(
            weight_g=weight_g,
            height_mm=height_mm,
            width_mm=width_mm,
            depth_mm=depth_mm,
            neck_diameter_mm=neck_diameter_mm,
            cap_height_mm=cap_height_mm,
            label_top_offset_mm=label_top_offset_mm,
            label_width_mm=label_width_mm,
            label_height_mm=label_height_mm,
            liquid_volume_ml=liquid_volume_ml,
            sku_code=sku_code,
            barcode=barcode,
        )

        observed_signature = build_signature(front, side, top, manual)

    if not (front and side and top):
        raise HTTPException(status_code=400, detail="Upload all three required 3-axis photos: front image, side image, and top image. Optional physical measurements are not required.")

    if len(observed_signature) < 8:
        raise HTTPException(status_code=400, detail="Could not build enough observed signature parameters from the uploaded 3-axis photos. Upload clearer front, side, and top images.")

    result = find_best_match(observed_signature, candidates)
    result["observed_signature_parameter_count"] = len(observed_signature)
    result["observed_signature"] = observed_signature

    best = result.get("best_match") or {}
    decision = ((best.get("match") or {}).get("decision")) or "NO_MATCH"
    insert_log(
        "IDENTIFY_BOTTLE",
        decision,
        f"Identification completed with decision {decision}",
        request={
            "front_image": bool(front),
            "side_image": bool(side),
            "top_image": bool(top),
            "optional_inputs_used": bool(manual),
        },
        response={
            "best_match": {
                "bottle_id": best.get("bottle_id"),
                "brand": best.get("brand"),
                "product_name": best.get("product_name"),
                "sku_code": best.get("sku_code"),
                "decision": decision,
                "score_percent": (best.get("match") or {}).get("score_percent"),
                "no_match_reasons": (best.get("match") or {}).get("no_match_reasons"),
            },
            "observed_signature_parameter_count": len(observed_signature),
        },
    )

    return result


@app.post("/compare/{bottle_id}")
async def compare_with_bottle(
    bottle_id: int,
    front_image: Optional[UploadFile] = File(None),
    side_image: Optional[UploadFile] = File(None),
    top_image: Optional[UploadFile] = File(None),
    weight_g: Optional[str] = Form(None),
    height_mm: Optional[str] = Form(None),
    width_mm: Optional[str] = Form(None),
    depth_mm: Optional[str] = Form(None),
    neck_diameter_mm: Optional[str] = Form(None),
    cap_height_mm: Optional[str] = Form(None),
    label_top_offset_mm: Optional[str] = Form(None),
    label_width_mm: Optional[str] = Form(None),
    label_height_mm: Optional[str] = Form(None),
):
    master = get_bottle(bottle_id)
    if not master:
        raise HTTPException(status_code=404, detail="Bottle not found")

    processing_match_id = f"PBM-{uuid.uuid4().hex[:10].upper()}"

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        front = await _save_upload(front_image, folder, "front")
        side = await _save_upload(side_image, folder, "side")
        top = await _save_upload(top_image, folder, "top")

        if not (front and side and top):
            raise HTTPException(status_code=400, detail="Upload all three required 3-axis photos: front image, side image, and top image.")

        observed_capture_ai = analyze_capture_set(front, side, top)

        manual = _manual_dict(
            weight_g=weight_g,
            height_mm=height_mm,
            width_mm=width_mm,
            depth_mm=depth_mm,
            neck_diameter_mm=neck_diameter_mm,
            cap_height_mm=cap_height_mm,
            label_top_offset_mm=label_top_offset_mm,
            label_width_mm=label_width_mm,
            label_height_mm=label_height_mm,
        )
        observed = build_signature(front, side, top, manual)
        visual_assets = {
            "master": master.get("image_assets", {}),
            "observed": create_asset_set(front, side, top, "processing_matches", processing_match_id),
        }

    match = compare_signatures(master["signature"], observed, master["tolerances"], master["weights"])
    master_capture_ai = master.get("capture_ai") or {}
    capture_ai_match = compare_capture_ai(master_capture_ai, observed_capture_ai)

    if not capture_ai_match.get("passed"):
        match.setdefault("no_match_reasons", []).append("AI capture quality / view / object-class gate failed")
        match["decision"] = "NO_MATCH"
    match["capture_ai_gate"] = capture_ai_match

    request_payload = {
        "bottle_id": bottle_id,
        "front_image": bool(front),
        "side_image": bool(side),
        "top_image": bool(top),
        "optional_inputs_used": bool(manual),
    }

    gate_results = {
        "capture_ai_gate": match.get("capture_ai_gate"),
        "distinctive_appearance_gate": match.get("distinctive_appearance_gate"),
        "preliminary_physical_gate": match.get("preliminary_physical_gate"),
        "controlled_geometry_gate": match.get("controlled_geometry_gate"),
        "color_gate": match.get("color_gate"),
        "primary_identity_gate": match.get("primary_identity_gate"),
        "category_gate": match.get("category_gate"),
        "exact_identifier_gate": match.get("exact_identifier_gate"),
        "dl_segmentation_gate": match.get("dl_segmentation_gate"),
        "ml_assisted_gate": match.get("ml_assisted_gate"),
    }

    processing_trace = [
        {"step": "input", "status": "PASS", "message": "Received front, side and top test sample photos."},
        {"step": "input.front", "status": "PASS", "message": "Front test sample image present."},
        {"step": "input.side", "status": "PASS", "message": "Side test sample image present."},
        {"step": "input.top", "status": "PASS", "message": "Top test sample image present."},
        {"step": "segmentation", "status": "PASS", "message": "Segmented bottle object and generated mask/overlay assets."},
    ]

    # Add segmentation-view details
    for view_name, view_data in ((visual_assets.get("observed", {}) or {}).get("views", {}) or {}).items():
        processing_trace.append({
            "step": f"segmentation.{view_name}",
            "status": "PASS",
            "message": f"{view_name.capitalize()} segmentation mode: {view_data.get('segmentation_mode') or '-'} | quality: {view_data.get('segmentation_quality')}",
        })

    # Gate-level status
    gate_steps = [
        ("capture_ai", "AI Capture Quality / View / Object Class Gate", match.get("capture_ai_gate")),
        ("distinctive_appearance", "Distinctive Object Appearance Gate", match.get("distinctive_appearance_gate")),
        ("physical_observation", "Preliminary Physical Characteristics Gate", match.get("preliminary_physical_gate")),
        ("controlled_geometry", "Controlled Geometry Gate", match.get("controlled_geometry_gate")),
        ("color", "Color Gate", match.get("color_gate")),
        ("primary_identity", "Primary Identity Gate", match.get("primary_identity_gate")),
        ("category", "Category Gate", match.get("category_gate")),
        ("exact_identifier", "Exact Identifier Gate", match.get("exact_identifier_gate")),
        ("dl_segmentation", "DL Segmentation Gate", match.get("dl_segmentation_gate")),
        ("ml_assisted", "ML-Assisted Feature Gate", match.get("ml_assisted_gate")),
    ]
    for gate_key, gate_label, gate_data in gate_steps:
        if gate_data is None:
            continue
        msg_parts = [f"{gate_label}: {'PASS' if gate_data.get('passed') else 'FAIL'}"]
        if gate_data.get("pass_rate") is not None:
            msg_parts.append(f"pass rate {round(float(gate_data.get('pass_rate')) * 100, 2)}%")
        if gate_data.get("average_quality_score") is not None:
            msg_parts.append(f"quality {gate_data.get('average_quality_score')}")
        if gate_data.get("compared_physical_parameters") is not None:
            msg_parts.append(f"physical parameters {gate_data.get('compared_physical_parameters')}")
        if gate_data.get("compared_parameters") is not None:
            msg_parts.append(f"parameters {gate_data.get('compared_parameters')}")
        if gate_data.get("compared_dl_parameters") is not None:
            msg_parts.append(f"DL parameters {gate_data.get('compared_dl_parameters')}")
        if gate_data.get("compared_ml_features") is not None:
            msg_parts.append(f"ML features {gate_data.get('compared_ml_features')}")
        if gate_data.get("mode") is not None:
            msg_parts.append(f"mode {gate_data.get('mode')}")
        processing_trace.append({
            "step": gate_key,
            "status": "PASS" if gate_data.get("passed") else "FAIL",
            "message": " | ".join(msg_parts),
        })

    # Every parameter-level check as scrolling status.
    # Disabled by default because hundreds of DOM log lines make the app feel slow.
    if detailed_parameter_trace():
        category_map = {
        "geometry": "geometry",
        "controlled_geometry": "geometry",
        "primary_identity": "primary",
        "category": "category",
        "color": "color",
        "ml_color": "ml",
        "ml_texture": "ml",
        "ml_shape": "ml",
        "ml_quality": "ml",
        "ml_geometry": "ml",
        "dl_segmentation": "dl",
        "exact_identifier": "exact",
    }
        for detail in match.get("details", []):
            status = "PASS" if detail.get("in_tolerance") else "FAIL"
            category = category_map.get(detail.get("category"), detail.get("category") or "misc")
            registered_value = detail.get("registered_value")
            observed_value = detail.get("observed_value")
            rel = detail.get("relative_difference")
            tol = detail.get("tolerance")
            message = (
                f"{detail.get('label')}: {status} | "
                f"registered={registered_value} | observed={observed_value} | "
                f"relative diff={rel} | tolerance={tol}"
            )
            processing_trace.append({
                "step": f"check.{category}.{detail.get('key')}",
                "status": status,
                "message": message,
            })
    else:
        passed = len([d for d in match.get("details", []) if d.get("in_tolerance")])
        failed = len([d for d in match.get("details", []) if not d.get("in_tolerance")])
        processing_trace.append({
            "step": "parameter_summary",
            "status": "INFO",
            "message": f"Parameter checks summarized for speed. PASS={passed}, FAIL={failed}. Set DETAILED_PARAMETER_TRACE=true for every check."
        })

    # Reasons and decision
    for idx, reason in enumerate(match.get("no_match_reasons", []), start=1):
        processing_trace.append({
            "step": f"reason.{idx}",
            "status": "FAIL",
            "message": reason,
        })

    processing_trace.append({
        "step": "decision",
        "status": match.get("decision", "NO_MATCH"),
        "message": f"Final decision: {match.get('decision')} with score {match.get('score_percent')}%.",
    })

    response = {
        "processing_match_id": processing_match_id,
        "bottle_id": bottle_id,
        "brand": master["brand"],
        "product_name": master["product_name"],
        "observed_signature": observed,
        "visual_assets": visual_assets,
        "master_capture_ai": master_capture_ai,
        "observed_capture_ai": observed_capture_ai,
        "capture_ai_match": capture_ai_match,
        "processing_trace": processing_trace,
        "match": match,
    }

    insert_processing_match({
        "processing_match_id": processing_match_id,
        "bottle_id": bottle_id,
        "brand": master["brand"],
        "product_name": master["product_name"],
        "decision": match.get("decision"),
        "score_percent": match.get("score_percent"),
        "compared_parameters": match.get("compared_parameters"),
        "no_match_reasons": match.get("no_match_reasons"),
        "request": request_payload,
        "observed_signature": observed,
        "gate_results": gate_results,
        "parameter_details": match.get("details"),
        "full_result": response,
        "visual_assets": visual_assets,
        "master_capture_ai": master_capture_ai,
        "observed_capture_ai": observed_capture_ai,
        "capture_ai_match": capture_ai_match,
    })

    insert_log(
        "PROCESSING_BOTTLE_MATCH",
        match.get("decision", "NO_MATCH"),
        f"Processing Bottle Match {processing_match_id} completed against bottle id {bottle_id}",
        request=request_payload,
        response={
            "processing_match_id": processing_match_id,
            "decision": match.get("decision"),
            "score_percent": match.get("score_percent"),
            "no_match_reasons": match.get("no_match_reasons"),
        },
    )

    return response
