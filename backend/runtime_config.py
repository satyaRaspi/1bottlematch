from __future__ import annotations

import os


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def processing_mode() -> str:
    return os.environ.get("BOTTLE_PROCESSING_MODE", "fast").strip().lower() or "fast"



def enable_overlays() -> bool:
    # Overlays are useful for demos, but expensive. Keep on by default for visual explanation.
    return env_bool("ENABLE_OVERLAYS", True)


def enable_real_dl() -> bool:
    # Real DL model inference should be explicitly enabled.
    return env_bool("ENABLE_REAL_DL", False)


def max_image_dim() -> int:
    try:
        return int(os.environ.get("MAX_IMAGE_DIM", "720"))
    except Exception:
        return 720


def detailed_parameter_trace() -> bool:
    # Huge status trace can slow browser rendering. Off by default.
    return env_bool("DETAILED_PARAMETER_TRACE", False)


def config_payload():
    return {
        "processing_mode": processing_mode(),
        "enable_overlays": enable_overlays(),
        "enable_real_dl": enable_real_dl(),
        "max_image_dim": max_image_dim(),
        "detailed_parameter_trace": detailed_parameter_trace(),
    }
