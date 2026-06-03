
"""
Bottle Signature Schema
Version: 1.6.0

This module defines the 50+ physical signature parameters used to identify bottles.
Each parameter is stored as a numeric value where possible, and compared with
a parameter-level tolerance and weight.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ParameterSpec:
    key: str
    label: str
    category: str
    unit: str
    default_weight: float
    default_tolerance: float
    description: str


PARAMETERS: List[ParameterSpec] = [
    # Geometry
    ParameterSpec("height_px", "Detected bottle height", "geometry", "px", 8.0, 0.06, "Measured from detected contour bounding box"),
    ParameterSpec("width_px", "Detected bottle width", "geometry", "px", 8.0, 0.06, "Measured from detected contour bounding box"),
    ParameterSpec("aspect_ratio", "Height to width ratio", "geometry", "ratio", 7.0, 0.05, "Bottle height divided by width"),
    ParameterSpec("area_ratio", "Bottle area ratio", "geometry", "ratio", 5.0, 0.08, "Contour area divided by bounding rectangle area"),
    ParameterSpec("contour_extent", "Contour extent", "geometry", "ratio", 4.0, 0.08, "Filled area ratio of bottle contour"),
    ParameterSpec("solidity", "Contour solidity", "geometry", "ratio", 4.0, 0.06, "Contour area divided by convex hull area"),
    ParameterSpec("perimeter_norm", "Normalized perimeter", "geometry", "ratio", 4.0, 0.08, "Perimeter normalized by bbox size"),
    ParameterSpec("top_width_ratio", "Top width ratio", "geometry", "ratio", 6.0, 0.08, "Approximate top/neck width vs max width"),
    ParameterSpec("mid_width_ratio", "Middle body width ratio", "geometry", "ratio", 5.0, 0.06, "Approximate middle width vs max width"),
    ParameterSpec("bottom_width_ratio", "Bottom width ratio", "geometry", "ratio", 6.0, 0.06, "Approximate base width vs max width"),
    ParameterSpec("shoulder_left_slope", "Left shoulder slope", "geometry", "ratio", 5.0, 0.12, "Contour slope around shoulder"),
    ParameterSpec("shoulder_right_slope", "Right shoulder slope", "geometry", "ratio", 5.0, 0.12, "Contour slope around shoulder"),
    ParameterSpec("symmetry_score", "Bottle symmetry score", "geometry", "ratio", 5.0, 0.08, "Left/right contour similarity"),
    ParameterSpec("neck_height_ratio", "Neck height ratio", "geometry", "ratio", 6.0, 0.10, "Estimated neck height vs total height"),
    ParameterSpec("shoulder_height_ratio", "Shoulder height ratio", "geometry", "ratio", 5.0, 0.10, "Estimated shoulder height vs total height"),

    # Top/cap/closure
    ParameterSpec("cap_width_ratio", "Cap width ratio", "closure", "ratio", 5.0, 0.10, "Top closure width vs max body width"),
    ParameterSpec("cap_height_ratio", "Cap height ratio", "closure", "ratio", 4.0, 0.15, "Estimated cap height vs total height"),
    ParameterSpec("top_circularity", "Top circularity", "closure", "ratio", 4.0, 0.12, "Circularity from top camera when available"),
    ParameterSpec("seal_band_ratio", "Seal band ratio", "closure", "ratio", 4.0, 0.15, "Estimated seal band region ratio"),
    ParameterSpec("closure_color_r", "Closure dominant red", "closure", "0-255", 2.5, 0.12, "Dominant cap/seal color component"),
    ParameterSpec("closure_color_g", "Closure dominant green", "closure", "0-255", 2.5, 0.12, "Dominant cap/seal color component"),
    ParameterSpec("closure_color_b", "Closure dominant blue", "closure", "0-255", 2.5, 0.12, "Dominant cap/seal color component"),

    # Label/packaging geometry
    ParameterSpec("front_label_top_ratio", "Front label top offset", "label", "ratio", 5.0, 0.12, "Estimated top offset of main label"),
    ParameterSpec("front_label_height_ratio", "Front label height ratio", "label", "ratio", 5.0, 0.12, "Estimated main label height vs bottle height"),
    ParameterSpec("front_label_width_ratio", "Front label width ratio", "label", "ratio", 5.0, 0.12, "Estimated main label width vs bottle width"),
    ParameterSpec("label_color_r", "Label dominant red", "label", "0-255", 3.0, 0.15, "Dominant label region color"),
    ParameterSpec("label_color_g", "Label dominant green", "label", "0-255", 3.0, 0.15, "Dominant label region color"),
    ParameterSpec("label_color_b", "Label dominant blue", "label", "0-255", 3.0, 0.15, "Dominant label region color"),
    ParameterSpec("label_edge_density", "Label edge density", "label", "ratio", 4.0, 0.20, "Edge/text density in label region"),
    ParameterSpec("barcode_region_score", "Barcode region score", "label", "ratio", 5.0, 0.25, "Heuristic barcode-like vertical edge score"),
    ParameterSpec("excise_mark_region_score", "Excise mark score", "label", "ratio", 5.0, 0.25, "Heuristic excise-label region score"),
    ParameterSpec("logo_region_density", "Logo region density", "label", "ratio", 4.0, 0.25, "Shape/edge density in logo-like area"),

    # Material/color/liquid
    ParameterSpec("glass_color_r", "Glass dominant red", "material", "0-255", 3.0, 0.12, "Dominant color outside label region"),
    ParameterSpec("glass_color_g", "Glass dominant green", "material", "0-255", 3.0, 0.12, "Dominant color outside label region"),
    ParameterSpec("glass_color_b", "Glass dominant blue", "material", "0-255", 3.0, 0.12, "Dominant color outside label region"),
    ParameterSpec("transparency_score", "Transparency score", "material", "ratio", 3.0, 0.20, "Brightness variance proxy"),
    ParameterSpec("reflection_score", "Reflection score", "material", "ratio", 2.5, 0.25, "Specular highlight proxy"),
    ParameterSpec("surface_texture_score", "Surface texture score", "material", "ratio", 2.5, 0.25, "Local texture/edge proxy"),
    ParameterSpec("liquid_color_r", "Liquid dominant red", "liquid", "0-255", 3.0, 0.15, "Dominant liquid/body color"),
    ParameterSpec("liquid_color_g", "Liquid dominant green", "liquid", "0-255", 3.0, 0.15, "Dominant liquid/body color"),
    ParameterSpec("liquid_color_b", "Liquid dominant blue", "liquid", "0-255", 3.0, 0.15, "Dominant liquid/body color"),
    ParameterSpec("fill_level_ratio", "Fill level ratio", "liquid", "ratio", 5.0, 0.10, "Estimated fill level if visible"),

    # Bottom/base
    ParameterSpec("base_width_ratio", "Base width ratio", "base", "ratio", 5.0, 0.08, "Base width vs max body width"),
    ParameterSpec("punt_depth_proxy", "Punt depth proxy", "base", "ratio", 3.0, 0.25, "Bottom indentation proxy from top/side"),
    ParameterSpec("bottom_ring_score", "Bottom ring score", "base", "ratio", 3.0, 0.25, "Ring pattern proxy"),

    # Sensor/manual values
    ParameterSpec("weight_g", "Measured weight", "sensor", "g", 8.0, 0.04, "Load cell/manual weight"),
    ParameterSpec("height_mm", "Physical height", "sensor", "mm", 8.0, 0.02, "Manual/calibrated physical height"),
    ParameterSpec("width_mm", "Physical width/diameter", "sensor", "mm", 8.0, 0.03, "Manual/calibrated physical width"),
    ParameterSpec("depth_mm", "Physical depth", "sensor", "mm", 7.0, 0.03, "Manual/calibrated physical depth"),
    ParameterSpec("neck_diameter_mm", "Neck diameter", "sensor", "mm", 7.0, 0.03, "Manual/calibrated neck diameter"),
    ParameterSpec("cap_height_mm", "Cap height", "sensor", "mm", 5.0, 0.05, "Manual/calibrated cap height"),
    ParameterSpec("label_top_offset_mm", "Label top offset", "sensor", "mm", 5.0, 0.05, "Manual/calibrated label offset"),
    ParameterSpec("label_width_mm", "Label width", "sensor", "mm", 5.0, 0.05, "Manual/calibrated label width"),
    ParameterSpec("label_height_mm", "Label height", "sensor", "mm", 5.0, 0.05, "Manual/calibrated label height"),
    ParameterSpec("liquid_volume_ml", "Declared liquid quantity", "sensor", "ml", 6.0, 0.01, "Declared/known quantity such as 180/375/750/1000 ml"),
    ParameterSpec("sku_code_numeric", "SKU code numeric", "metadata", "hash", 4.0, 0.00, "Optional controlled numeric SKU code"),
    ParameterSpec("barcode_numeric_hash", "Barcode numeric hash", "metadata", "hash", 6.0, 0.00, "Optional barcode/excise code hash"),
]


# ML-assisted feature parameters appended in v1.6.0.
ML_ASSISTED_PARAMETER_SPECS = []
for view in ["front", "side", "top"]:
    for cluster_idx in [1, 2]:
        ML_ASSISTED_PARAMETER_SPECS.extend([
            ParameterSpec(f"ml_{view}_kmeans_r{cluster_idx}", f"ML {view} dominant color {cluster_idx} red", "ml_color", "0-255", 3.5, 0.13, "K-means dominant color cluster red channel"),
            ParameterSpec(f"ml_{view}_kmeans_g{cluster_idx}", f"ML {view} dominant color {cluster_idx} green", "ml_color", "0-255", 3.5, 0.13, "K-means dominant color cluster green channel"),
            ParameterSpec(f"ml_{view}_kmeans_b{cluster_idx}", f"ML {view} dominant color {cluster_idx} blue", "ml_color", "0-255", 3.5, 0.13, "K-means dominant color cluster blue channel"),
        ])
    ML_ASSISTED_PARAMETER_SPECS.extend([
        ParameterSpec(f"ml_{view}_color_cluster_compactness", f"ML {view} color cluster compactness", "ml_color", "ratio", 2.0, 0.25, "K-means compactness proxy"),
        ParameterSpec(f"ml_{view}_orb_keypoint_density", f"ML {view} ORB keypoint density", "ml_texture", "ratio", 3.0, 0.25, "ORB feature/keypoint density"),
        ParameterSpec(f"ml_{view}_texture_complexity", f"ML {view} texture complexity", "ml_texture", "ratio", 3.0, 0.25, "Laplacian texture complexity"),
        ParameterSpec(f"ml_{view}_bbox_w", f"ML {view} object bbox width", "ml_geometry", "px", 4.0, 0.06, "ML-assisted object region width"),
        ParameterSpec(f"ml_{view}_bbox_h", f"ML {view} object bbox height", "ml_geometry", "px", 4.0, 0.06, "ML-assisted object region height"),
        ParameterSpec(f"ml_{view}_bbox_aspect", f"ML {view} bbox aspect", "ml_geometry", "ratio", 4.0, 0.05, "ML-assisted object bounding-box aspect"),
        ParameterSpec(f"ml_{view}_quality", f"ML {view} capture quality", "ml_quality", "ratio", 2.5, 0.20, "Capture quality score"),
    ])
    for i in range(8):
        ML_ASSISTED_PARAMETER_SPECS.append(ParameterSpec(f"ml_{view}_gradient_h{i}", f"ML {view} gradient histogram {i}", "ml_shape", "ratio", 3.0, 0.18, "Gradient-orientation histogram bin"))

ML_ASSISTED_PARAMETER_SPECS.extend([
    ParameterSpec("ml_cross_view_shape_consistency", "ML cross-view shape consistency", "ml_quality", "ratio", 3.5, 0.18, "Consistency of shape profile across 3 views"),
    ParameterSpec("ml_cross_view_color_consistency", "ML cross-view color consistency", "ml_quality", "ratio", 3.5, 0.18, "Consistency of dominant color across 3 views"),
    ParameterSpec("ml_capture_quality_score", "ML capture quality score", "ml_quality", "ratio", 3.5, 0.15, "Overall capture quality score"),
    ParameterSpec("ml_assisted_enabled", "ML-assisted extraction enabled", "ml_quality", "flag", 1.0, 0.0, "Whether ML-assisted features were extracted"),
])
PARAMETERS.extend(ML_ASSISTED_PARAMETER_SPECS)


# Light deep-learning segmentation parameters - v1.6.0.
DL_SEGMENTATION_PARAMETER_SPECS = []
for view_prefix, view_label in [("", "front"), ("side_", "side"), ("top_", "top")]:
    DL_SEGMENTATION_PARAMETER_SPECS.extend([
        ParameterSpec(f"{view_prefix}dl_mask_fill_ratio", f"DL {view_label} mask fill ratio", "dl_segmentation", "ratio", 4.0, 0.10, "Object mask fill ratio from DL/fallback segmentation"),
        ParameterSpec(f"{view_prefix}dl_mask_bbox_w", f"DL {view_label} mask bbox width", "dl_segmentation", "px", 5.0, 0.05, "Bottle mask bounding box width"),
        ParameterSpec(f"{view_prefix}dl_mask_bbox_h", f"DL {view_label} mask bbox height", "dl_segmentation", "px", 5.0, 0.05, "Bottle mask bounding box height"),
        ParameterSpec(f"{view_prefix}dl_mask_contour_area", f"DL {view_label} mask contour area", "dl_segmentation", "px2", 4.0, 0.08, "Bottle mask contour area"),
        ParameterSpec(f"{view_prefix}dl_mask_quality_score", f"DL {view_label} mask quality score", "dl_segmentation", "ratio", 3.0, 0.12, "Segmentation quality score"),
        ParameterSpec(f"{view_prefix}dl_segmentation_enabled", f"DL {view_label} ONNX segmentation enabled", "dl_segmentation", "flag", 1.0, 0.0, "Whether ONNX segmentation was used"),
        ParameterSpec(f"{view_prefix}dl_segmentation_real_model_used", f"DL {view_label} real model used", "dl_segmentation", "flag", 1.0, 0.0, "Whether a real ultralytics/ONNX model was used"),
        ParameterSpec(f"{view_prefix}dl_segmentation_fallback", f"DL {view_label} segmentation fallback", "dl_segmentation", "flag", 1.0, 0.0, "Whether OpenCV fallback was used"),
    ])
PARAMETERS.extend(DL_SEGMENTATION_PARAMETER_SPECS)


# Distinctive object appearance parameters — v1.6.0.
DISTINCTIVE_APPEARANCE_PARAMETER_SPECS = [
    ParameterSpec("opaque_surface_score", "Opaque surface score", "appearance", "ratio", 8.0, 0.08, "High for painted/opaque bottles; low for transparent bottles"),
    ParameterSpec("transparent_surface_score", "Transparent surface score", "appearance", "ratio", 8.0, 0.08, "High for transparent plastic/glass bottles"),
    ParameterSpec("yellow_dominance_score", "Yellow dominance score", "appearance", "ratio", 8.0, 0.10, "High for yellow objects"),
    ParameterSpec("dark_cap_score", "Dark cap score", "appearance", "ratio", 4.5, 0.15, "Dark cap/closure proxy"),
    ParameterSpec("body_saturation_score", "Body saturation score", "appearance", "ratio", 7.0, 0.10, "Median saturation of body region"),
    ParameterSpec("contour_saturation_score", "Whole object saturation score", "appearance", "ratio", 7.0, 0.10, "Median saturation of object contour"),
]
PARAMETERS.extend(DISTINCTIVE_APPEARANCE_PARAMETER_SPECS)


PARAMETER_INDEX: Dict[str, ParameterSpec] = {p.key: p for p in PARAMETERS}


def default_weights() -> Dict[str, float]:
    return {p.key: p.default_weight for p in PARAMETERS}


def default_tolerances() -> Dict[str, float]:
    return {p.key: p.default_tolerance for p in PARAMETERS}
