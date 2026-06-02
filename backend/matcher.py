
from __future__ import annotations

from typing import Dict, List, Tuple
from signature_schema import PARAMETERS, default_tolerances, default_weights
from ml_features import cosine_similarity_from_signatures, euclidean_similarity_from_signatures, ML_VECTOR_KEYS

# Tightened matching rules - v1.5.7
MIN_MATCH_SCORE = 0.90
MIN_COMPARED_PARAMETERS = 24
MIN_PRIMARY_GATE_PASS_RATE = 0.82
MIN_CATEGORY_PASS_RATE = 0.70
MAX_MAJOR_PARAMETER_FAILURES = 4

# Color is now stricter than v1.5.7
COLOR_MAX_RELATIVE_DIFFERENCE = 0.16
COLOR_MIN_PASS_RATE = 0.82

# Controlled capture rules. Since photos are taken at the same height,
# same distance, same background and same 3-axis setup, geometry can be used
# as a primary hard gate rather than a loose visual similarity score.
CONTROLLED_GEOMETRY_MIN_PASS_RATE = 0.88
CONTROLLED_GEOMETRY_MAX_MAJOR_FAILURES = 2
CONTROLLED_GEOMETRY_STRICT_TOLERANCE_MULTIPLIER = 0.55
ML_ASSISTED_MIN_COSINE_SIMILARITY = 0.86
ML_ASSISTED_MIN_EUCLIDEAN_SIMILARITY = 0.78
ML_ASSISTED_WEIGHTED_BOOST_MAX = 0.035
DL_SEGMENTATION_MIN_QUALITY = 0.58
DL_SEGMENTATION_MIN_PASS_RATE = 0.66

COLOR_KEYS = [
    "label_color_r", "label_color_g", "label_color_b",
    "glass_color_r", "glass_color_g", "glass_color_b",
    "liquid_color_r", "liquid_color_g", "liquid_color_b",
    "closure_color_r", "closure_color_g", "closure_color_b",
]

# These are high-identity parameters. If many of these fail, it is a no match
# even if the overall average score looks acceptable.
PRIMARY_IDENTITY_KEYS = [
    "height_px", "width_px", "aspect_ratio",
    "top_width_ratio", "mid_width_ratio", "bottom_width_ratio",
    "symmetry_score", "neck_height_ratio", "shoulder_height_ratio",
    "cap_width_ratio", "front_label_top_ratio",
    "front_label_height_ratio", "front_label_width_ratio",
    "base_width_ratio",
    "height_mm", "width_mm", "depth_mm",
    "neck_diameter_mm", "cap_height_mm",
    "label_top_offset_mm", "label_width_mm", "label_height_mm",
    "weight_g", "liquid_volume_ml",
    "barcode_numeric_hash", "sku_code_numeric",
]

CONTROLLED_GEOMETRY_KEYS = [
    "height_px",
    "width_px",
    "aspect_ratio",
    "contour_extent",
    "solidity",
    "perimeter_norm",
    "top_width_ratio",
    "mid_width_ratio",
    "bottom_width_ratio",
    "shoulder_left_slope",
    "shoulder_right_slope",
    "symmetry_score",
    "neck_height_ratio",
    "shoulder_height_ratio",
    "cap_width_ratio",
    "cap_height_ratio",
    "front_label_top_ratio",
    "front_label_height_ratio",
    "front_label_width_ratio",
    "base_width_ratio",
    "side_aspect_ratio",
    "side_contour_extent",
    "side_shoulder_height_ratio",
    "top_circularity",
]

# Optional exact-match style identifiers. If present on both sides and fail, no match.

# Preliminary physical characteristics gate.
# This is the earliest bottle-object sanity check. It compares the observed
# object's physical traits against the registered bottle before the stricter
# final gates are considered.
PRELIMINARY_PHYSICAL_MIN_PASS_RATE = 0.84
PRELIMINARY_PHYSICAL_MAX_MAJOR_FAILURES = 3
DISTINCTIVE_APPEARANCE_MIN_PASS_RATE = 0.72
DISTINCTIVE_APPEARANCE_KEYS = [
    "opaque_surface_score",
    "transparent_surface_score",
    "yellow_dominance_score",
    "body_saturation_score",
    "contour_saturation_score",
    "glass_color_r", "glass_color_g", "glass_color_b",
    "liquid_color_r", "liquid_color_g", "liquid_color_b",
    "label_color_r", "label_color_g", "label_color_b",
    "closure_color_r", "closure_color_g", "closure_color_b",
]

PRELIMINARY_PHYSICAL_KEYS = [
    "height_px", "width_px", "aspect_ratio",
    "contour_extent", "solidity", "perimeter_norm",
    "top_width_ratio", "mid_width_ratio", "bottom_width_ratio",
    "shoulder_left_slope", "shoulder_right_slope",
    "symmetry_score",
    "neck_height_ratio", "shoulder_height_ratio",
    "cap_width_ratio", "cap_height_ratio",
    "front_label_top_ratio", "front_label_height_ratio", "front_label_width_ratio",
    "base_width_ratio",
    "depth_px", "side_aspect_ratio", "side_contour_extent", "side_shoulder_height_ratio",
    "top_circularity",
    "dl_mask_bbox_w", "dl_mask_bbox_h", "dl_mask_fill_ratio", "dl_mask_contour_area",
    "side_dl_mask_bbox_w", "side_dl_mask_bbox_h", "side_dl_mask_fill_ratio", "side_dl_mask_contour_area",
    "top_dl_mask_bbox_w", "top_dl_mask_bbox_h", "top_dl_mask_fill_ratio", "top_dl_mask_contour_area",
]

DL_SEGMENTATION_KEYS = [
    "dl_mask_quality_score", "dl_mask_bbox_w", "dl_mask_bbox_h", "dl_mask_fill_ratio",
    "side_dl_mask_quality_score", "side_dl_mask_bbox_w", "side_dl_mask_bbox_h", "side_dl_mask_fill_ratio",
    "top_dl_mask_quality_score", "top_dl_mask_bbox_w", "top_dl_mask_bbox_h", "top_dl_mask_fill_ratio",
]

EXACT_OR_NEAR_EXACT_KEYS = [
    "barcode_numeric_hash",
    "sku_code_numeric",
    "liquid_volume_ml",
]


def _relative_difference(a: float, b: float) -> float:
    denom = max(abs(a), abs(b), 1.0)
    return abs(a - b) / denom


def parameter_score(master_value: float, observed_value: float, tolerance: float) -> Tuple[float, bool, float]:
    """
    Strict parameter-level scoring.

    Within tolerance:
      score remains high but still rewards closeness.

    Outside tolerance:
      score decays aggressively so a few bad high-weight dimensions cannot be hidden
      by many low-value similarities.
    """
    diff = _relative_difference(master_value, observed_value)
    if tolerance <= 0:
        in_tol = diff == 0
        return (1.0 if in_tol else 0.0), in_tol, diff

    in_tol = diff <= tolerance
    if in_tol:
        score = 1.0 - (diff / max(tolerance, 1e-9)) * 0.20
    else:
        over = (diff - tolerance) / max(tolerance, 1e-9)
        score = max(0.0, 0.75 - over * 0.55)
    return float(score), bool(in_tol), float(diff)


def color_gate(master: Dict[str, float], observed: Dict[str, float]) -> Dict:
    """
    Hard no-match rule:
    If comparable color characteristics are materially different, the result is NO_MATCH.
    v1.5.7 tightens this using both individual failure and pass-rate logic.
    """
    compared = []
    failed = []

    for key in COLOR_KEYS:
        if key not in master or key not in observed:
            continue
        try:
            mv = float(master[key])
            ov = float(observed[key])
        except Exception:
            continue

        diff = _relative_difference(mv, ov)
        item = {
            "key": key,
            "master_value": round(mv, 3),
            "observed_value": round(ov, 3),
            "relative_difference": round(diff, 5),
            "max_allowed_difference": COLOR_MAX_RELATIVE_DIFFERENCE,
            "passed": diff <= COLOR_MAX_RELATIVE_DIFFERENCE,
        }
        compared.append(item)
        if diff > COLOR_MAX_RELATIVE_DIFFERENCE:
            failed.append(item)

    pass_rate = (len(compared) - len(failed)) / len(compared) if compared else 1.0

    return {
        "passed": len(failed) == 0 and pass_rate >= COLOR_MIN_PASS_RATE,
        "pass_rate": round(pass_rate, 4),
        "minimum_required_pass_rate": COLOR_MIN_PASS_RATE,
        "compared_color_parameters": len(compared),
        "failed_color_parameters": failed,
        "details": compared,
    }




def _distinctive_appearance_gate(details: List[Dict]) -> Dict:
    """
    Hard gate for obvious visual-class mismatch.

    This catches cases like:
    - transparent soda bottle vs opaque yellow steel/plastic bottle
    - clear bottle vs colored bottle
    - label/color family mismatch
    """
    rows = [d for d in details if d["key"] in DISTINCTIVE_APPEARANCE_KEYS]
    failed = [d for d in rows if not d["in_tolerance"]]
    pass_rate = (len(rows) - len(failed)) / len(rows) if rows else 1.0
    critical_failures = [
        d for d in failed
        if d["key"] in [
            "opaque_surface_score",
            "transparent_surface_score",
            "yellow_dominance_score",
            "body_saturation_score",
            "contour_saturation_score",
        ]
    ]
    return {
        "passed": pass_rate >= DISTINCTIVE_APPEARANCE_MIN_PASS_RATE and len(critical_failures) <= 1,
        "mode": "distinctive_object_appearance",
        "pass_rate": round(pass_rate, 4),
        "minimum_required_pass_rate": DISTINCTIVE_APPEARANCE_MIN_PASS_RATE,
        "compared_appearance_parameters": len(rows),
        "failed_appearance_parameters": failed,
        "critical_appearance_failures": critical_failures,
        "keys_used": DISTINCTIVE_APPEARANCE_KEYS,
    }


def _preliminary_physical_gate(details: List[Dict]) -> Dict:
    """
    Preliminary gate based on object-level physical characteristics.

    This gate answers: "Does the test sample physically look like the same kind
    of bottle object before we go deeper into color, label, ML and final scoring?"

    It compares broad but important physical characteristics:
    - object height/width/aspect
    - contour solidity/extent/perimeter
    - neck/shoulder/cap/base ratios
    - label placement ratios
    - side/top profile
    - DL/fallback segmentation mask geometry
    """
    physical = [d for d in details if d["key"] in PRELIMINARY_PHYSICAL_KEYS]
    failed = [d for d in physical if not d["in_tolerance"]]
    pass_rate = (len(physical) - len(failed)) / len(physical) if physical else 0.0

    major_failures = [
        d for d in failed
        if d["weight"] >= 4.0 or d["relative_difference"] > max(d["tolerance"] * 1.65, 0.055)
    ]

    # Group failures by category for easier explanation.
    category_failure_counts = {}
    for d in failed:
        category_failure_counts[d["category"]] = category_failure_counts.get(d["category"], 0) + 1

    return {
        "passed": bool(physical)
                  and pass_rate >= PRELIMINARY_PHYSICAL_MIN_PASS_RATE
                  and len(major_failures) <= PRELIMINARY_PHYSICAL_MAX_MAJOR_FAILURES,
        "mode": "preliminary_physical_object_characteristics",
        "pass_rate": round(pass_rate, 4),
        "minimum_required_pass_rate": PRELIMINARY_PHYSICAL_MIN_PASS_RATE,
        "compared_physical_parameters": len(physical),
        "failed_physical_parameters": failed,
        "major_physical_failures": major_failures,
        "max_major_physical_failures": PRELIMINARY_PHYSICAL_MAX_MAJOR_FAILURES,
        "category_failure_counts": category_failure_counts,
        "keys_used": PRELIMINARY_PHYSICAL_KEYS,
    }


def _controlled_geometry_gate(details: List[Dict]) -> Dict:
    """
    Hard gate for controlled 3-axis capture.

    Because registration and identification photos are captured at the same
    height, distance and background, geometric parameters are repeatable and
    should be treated as primary identity evidence.

    If this gate fails, the bottle is NO_MATCH even when other features look similar.
    """
    geometry = [d for d in details if d["key"] in CONTROLLED_GEOMETRY_KEYS]
    failed = [d for d in geometry if not d["in_tolerance"]]

    pass_rate = (len(geometry) - len(failed)) / len(geometry) if geometry else 0.0

    major_failures = [
        d for d in failed
        if d["relative_difference"] > max(d["tolerance"] * 1.6, 0.045)
    ]

    return {
        "passed": bool(geometry)
                  and pass_rate >= CONTROLLED_GEOMETRY_MIN_PASS_RATE
                  and len(major_failures) <= CONTROLLED_GEOMETRY_MAX_MAJOR_FAILURES,
        "mode": "controlled_3_axis_fixed_height_distance_background",
        "pass_rate": round(pass_rate, 4),
        "minimum_required_pass_rate": CONTROLLED_GEOMETRY_MIN_PASS_RATE,
        "compared_geometry_parameters": len(geometry),
        "failed_geometry_parameters": failed,
        "major_geometry_failures": major_failures,
        "max_major_geometry_failures": CONTROLLED_GEOMETRY_MAX_MAJOR_FAILURES,
        "keys_used": CONTROLLED_GEOMETRY_KEYS,
    }


def _primary_gate(details: List[Dict]) -> Dict:
    primary = [d for d in details if d["key"] in PRIMARY_IDENTITY_KEYS]
    failed = [d for d in primary if not d["in_tolerance"]]
    pass_rate = (len(primary) - len(failed)) / len(primary) if primary else 0.0

    major_failures = [
        d for d in failed
        if d["weight"] >= 5.0 or d["relative_difference"] > max(d["tolerance"] * 1.8, 0.08)
    ]

    return {
        "passed": bool(primary) and pass_rate >= MIN_PRIMARY_GATE_PASS_RATE and len(major_failures) <= MAX_MAJOR_PARAMETER_FAILURES,
        "pass_rate": round(pass_rate, 4),
        "minimum_required_pass_rate": MIN_PRIMARY_GATE_PASS_RATE,
        "compared_primary_parameters": len(primary),
        "failed_primary_parameters": failed,
        "major_failures": major_failures,
        "max_major_parameter_failures": MAX_MAJOR_PARAMETER_FAILURES,
    }


def _category_gate(details: List[Dict]) -> Dict:
    categories = {}
    for d in details:
        cat = d["category"]
        categories.setdefault(cat, {"total": 0, "passed": 0, "failed": []})
        categories[cat]["total"] += 1
        if d["in_tolerance"]:
            categories[cat]["passed"] += 1
        else:
            categories[cat]["failed"].append(d)

    category_results = {}
    failed_categories = []
    for cat, data in categories.items():
        rate = data["passed"] / data["total"] if data["total"] else 0.0
        category_results[cat] = {
            "pass_rate": round(rate, 4),
            "total": data["total"],
            "passed": data["passed"],
            "failed_count": len(data["failed"]),
        }
        # Only enforce on categories where we have enough comparable parameters.
        if data["total"] >= 3 and rate < MIN_CATEGORY_PASS_RATE:
            failed_categories.append(cat)

    return {
        "passed": len(failed_categories) == 0,
        "minimum_required_pass_rate": MIN_CATEGORY_PASS_RATE,
        "failed_categories": failed_categories,
        "categories": category_results,
    }


def _exact_identifier_gate(master: Dict[str, float], observed: Dict[str, float]) -> Dict:
    compared = []
    failed = []

    for key in EXACT_OR_NEAR_EXACT_KEYS:
        if key not in master or key not in observed:
            continue

        try:
            mv = float(master[key])
            ov = float(observed[key])
        except Exception:
            continue

        # Barcode/SKU hash must be exact. Quantity can tolerate 1%.
        allowed = 0.0 if key in ("barcode_numeric_hash", "sku_code_numeric") else 0.01
        diff = _relative_difference(mv, ov)
        item = {
            "key": key,
            "master_value": round(mv, 4),
            "observed_value": round(ov, 4),
            "relative_difference": round(diff, 5),
            "max_allowed_difference": allowed,
            "passed": diff <= allowed,
        }
        compared.append(item)
        if not item["passed"]:
            failed.append(item)

    return {
        "passed": len(failed) == 0,
        "compared_exact_parameters": len(compared),
        "failed_exact_parameters": failed,
        "details": compared,
    }




def _dl_segmentation_gate(master: Dict[str, float], observed: Dict[str, float], details: List[Dict]) -> Dict:
    quality_keys = [k for k in ["dl_mask_quality_score", "side_dl_mask_quality_score", "top_dl_mask_quality_score"] if k in observed]
    quality_scores = [float(observed.get(k, 0.0)) for k in quality_keys]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
    dl_details = [d for d in details if d["key"] in DL_SEGMENTATION_KEYS]
    passed_count = len([d for d in dl_details if d["in_tolerance"]])
    pass_rate = passed_count / len(dl_details) if dl_details else 1.0
    onnx_used = any(float(observed.get(k, 0.0)) == 1.0 for k in ["dl_segmentation_enabled", "side_dl_segmentation_enabled", "top_dl_segmentation_enabled"])
    passed = True
    reasons = []
    if quality_scores and avg_quality < DL_SEGMENTATION_MIN_QUALITY:
        passed = False; reasons.append("Segmentation quality below minimum threshold")
    if dl_details and pass_rate < DL_SEGMENTATION_MIN_PASS_RATE:
        passed = False; reasons.append("Segmentation mask geometry mismatch")
    return {"passed": passed, "enabled": True, "onnx_used": onnx_used, "mode": "onnx_runtime_cpu" if onnx_used else "opencv_grabcut_fallback", "average_quality_score": round(avg_quality,4), "minimum_quality_score": DL_SEGMENTATION_MIN_QUALITY, "mask_geometry_pass_rate": round(pass_rate,4), "minimum_mask_geometry_pass_rate": DL_SEGMENTATION_MIN_PASS_RATE, "compared_dl_parameters": len(dl_details), "failed_dl_parameters": [d for d in dl_details if not d["in_tolerance"]], "reasons": reasons}

def _ml_assisted_gate(master: Dict[str, float], observed: Dict[str, float]) -> Dict:
    comparable = [k for k in ML_VECTOR_KEYS if k in master and k in observed]
    if len(comparable) < 12:
        return {"passed": True, "enabled": False, "reason": "Insufficient ML-assisted features available; gate not enforced", "compared_ml_features": len(comparable), "cosine_similarity": None, "euclidean_similarity": None, "minimum_cosine_similarity": ML_ASSISTED_MIN_COSINE_SIMILARITY, "minimum_euclidean_similarity": ML_ASSISTED_MIN_EUCLIDEAN_SIMILARITY}
    cosine = cosine_similarity_from_signatures(master, observed)
    euclidean = euclidean_similarity_from_signatures(master, observed)
    passed = cosine >= ML_ASSISTED_MIN_COSINE_SIMILARITY and euclidean >= ML_ASSISTED_MIN_EUCLIDEAN_SIMILARITY
    return {"passed": passed, "enabled": True, "compared_ml_features": len(comparable), "cosine_similarity": round(cosine,4), "euclidean_similarity": round(euclidean,4), "minimum_cosine_similarity": ML_ASSISTED_MIN_COSINE_SIMILARITY, "minimum_euclidean_similarity": ML_ASSISTED_MIN_EUCLIDEAN_SIMILARITY, "feature_keys_used": comparable}

def compare_signatures(master: Dict[str, float], observed: Dict[str, float],
                       tolerances: Dict[str, float] | None = None,
                       weights: Dict[str, float] | None = None) -> Dict:
    tolerances = tolerances or default_tolerances()
    weights = weights or default_weights()

    details = []
    weighted_score_sum = 0.0
    weight_sum = 0.0
    matched_params = 0
    compared_params = 0

    for spec in PARAMETERS:
        key = spec.key
        if key not in master or key not in observed:
            continue
        try:
            mv = float(master[key])
            ov = float(observed[key])
        except Exception:
            continue

        weight = float(weights.get(key, spec.default_weight))
        tolerance = float(tolerances.get(key, spec.default_tolerance))

        # Tighten tolerances for controlled capture.
        # Geometry can be compared more strictly because the camera height,
        # distance, background and image setup are fixed.
        if key in DISTINCTIVE_APPEARANCE_KEYS and tolerance > 0:
            tolerance = min(tolerance * 0.55, 0.075)
        elif key in CONTROLLED_GEOMETRY_KEYS and tolerance > 0:
            tolerance = tolerance * CONTROLLED_GEOMETRY_STRICT_TOLERANCE_MULTIPLIER
        elif key in PRELIMINARY_PHYSICAL_KEYS and tolerance > 0:
            tolerance = tolerance * 0.70
        elif key in PRIMARY_IDENTITY_KEYS and tolerance > 0:
            tolerance = tolerance * 0.80

        if key in COLOR_KEYS:
            tolerance = min(tolerance, COLOR_MAX_RELATIVE_DIFFERENCE)

        score, in_tol, diff = parameter_score(mv, ov, tolerance)

        compared_params += 1
        if in_tol:
            matched_params += 1

        weighted_score_sum += score * weight
        weight_sum += weight

        details.append({
            "key": key,
            "label": spec.label,
            "category": spec.category,
            "master_value": round(mv, 4),
            "observed_value": round(ov, 4),
            "relative_difference": round(diff, 5),
            "tolerance": round(tolerance, 5),
            "weight": weight,
            "score": round(score, 4),
            "in_tolerance": in_tol,
        })

    final_score = weighted_score_sum / weight_sum if weight_sum else 0.0

    color_result = color_gate(master, observed)
    distinctive_appearance_result = _distinctive_appearance_gate(details)
    preliminary_physical_result = _preliminary_physical_gate(details)
    controlled_geometry_result = _controlled_geometry_gate(details)
    primary_result = _primary_gate(details)
    category_result = _category_gate(details)
    exact_result = _exact_identifier_gate(master, observed)
    ml_assisted_result = _ml_assisted_gate(master, observed)
    dl_segmentation_result = _dl_segmentation_gate(master, observed, details)

    if ml_assisted_result.get("enabled") and ml_assisted_result.get("passed"):
        ml_boost = min(ML_ASSISTED_WEIGHTED_BOOST_MAX, (ml_assisted_result.get("cosine_similarity", 0) - ML_ASSISTED_MIN_COSINE_SIMILARITY) * 0.08)
        final_score = min(1.0, final_score + max(0.0, ml_boost))

    no_match_reasons = []

    if compared_params < MIN_COMPARED_PARAMETERS:
        no_match_reasons.append(f"Insufficient comparable parameters: {compared_params}, minimum required {MIN_COMPARED_PARAMETERS}")

    if final_score < MIN_MATCH_SCORE:
        no_match_reasons.append("Match score below 90% tightened threshold")

    if not distinctive_appearance_result["passed"]:
        no_match_reasons.append("Distinctive object appearance mismatch")

    if not preliminary_physical_result["passed"]:
        no_match_reasons.append("Preliminary physical characteristics mismatch")

    if not controlled_geometry_result["passed"]:
        no_match_reasons.append("Controlled geometry mismatch")

    if not color_result["passed"]:
        no_match_reasons.append("Color mismatch detected")

    if not primary_result["passed"]:
        no_match_reasons.append("Primary identity gate failed")

    if not category_result["passed"]:
        no_match_reasons.append("One or more signature categories failed minimum pass rate")

    if not exact_result["passed"]:
        no_match_reasons.append("Exact identifier mismatch detected")

    if not dl_segmentation_result["passed"]:
        no_match_reasons.append("Light DL segmentation quality/mask gate failed")

    if ml_assisted_result.get("enabled") and not ml_assisted_result["passed"]:
        no_match_reasons.append("ML-assisted feature similarity gate failed")

    if no_match_reasons:
        decision = "NO_MATCH"
    elif final_score >= 0.96 and compared_params >= MIN_COMPARED_PARAMETERS:
        decision = "CONFIRMED_MATCH"
    elif final_score >= MIN_MATCH_SCORE and compared_params >= MIN_COMPARED_PARAMETERS:
        decision = "MATCH"
    else:
        decision = "NO_MATCH"
        no_match_reasons.append("Review-level result treated as no match")

    details.sort(key=lambda d: (not d["in_tolerance"], d["weight"]), reverse=True)

    return {
        "score": round(final_score, 4),
        "score_percent": round(final_score * 100, 2),
        "decision": decision,
        "minimum_required_score_percent": int(MIN_MATCH_SCORE * 100),
        "matched_parameters": matched_params,
        "compared_parameters": compared_params,
        "minimum_compared_parameters": MIN_COMPARED_PARAMETERS,
        "distinctive_appearance_gate": distinctive_appearance_result,
        "preliminary_physical_gate": preliminary_physical_result,
        "controlled_geometry_gate": controlled_geometry_result,
        "color_gate": color_result,
        "primary_identity_gate": primary_result,
        "category_gate": category_result,
        "exact_identifier_gate": exact_result,
        "dl_segmentation_gate": dl_segmentation_result,
        "ml_assisted_gate": ml_assisted_result,
        "no_match_reasons": no_match_reasons,
        "details": details,
    }


def find_best_match(observed: Dict[str, float], candidates: List[Dict]) -> Dict:
    best = None
    results = []

    for candidate in candidates:
        match = compare_signatures(candidate["signature"], observed,
                                   candidate.get("tolerances"), candidate.get("weights"))
        item = {
            "bottle_id": candidate["id"],
            "brand": candidate.get("brand", ""),
            "product_name": candidate.get("product_name", ""),
            "sku_code": candidate.get("sku_code", ""),
            "quantity_ml": candidate.get("quantity_ml", ""),
            "match": match,
        }
        results.append(item)
        if best is None or item["match"]["score"] > best["match"]["score"]:
            best = item

    results.sort(key=lambda x: x["match"]["score"], reverse=True)
    return {
        "best_match": best,
        "ranked_matches": results[:10],
    }
