
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

DB_PATH = Path(__file__).parent / "bottle_signatures.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS bottles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            product_name TEXT NOT NULL,
            sku_code TEXT,
            quantity_ml REAL,
            color TEXT,
            barcode TEXT,
            notes TEXT,
            signature_json TEXT NOT NULL,
            tolerances_json TEXT,
            weights_json TEXT,
            image_assets_json TEXT,
            capture_ai_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            request_json TEXT,
            response_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS processing_bottle_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processing_match_id TEXT UNIQUE NOT NULL,
            bottle_id INTEGER,
            brand TEXT,
            product_name TEXT,
            decision TEXT,
            score_percent REAL,
            compared_parameters INTEGER,
            no_match_reasons_json TEXT,
            request_json TEXT,
            observed_signature_json TEXT,
            gate_results_json TEXT,
            parameter_details_json TEXT,
            full_result_json TEXT,
            visual_assets_json TEXT,
            master_capture_ai_json TEXT,
            observed_capture_ai_json TEXT,
            capture_ai_match_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # Backward-compatible migrations
        if not _column_exists(conn, 'bottles', 'image_assets_json'):
            conn.execute("ALTER TABLE bottles ADD COLUMN image_assets_json TEXT")
        if not _column_exists(conn, 'processing_bottle_matches', 'visual_assets_json'):
            conn.execute("ALTER TABLE processing_bottle_matches ADD COLUMN visual_assets_json TEXT")
        if not _column_exists(conn, 'bottles', 'capture_ai_json'):
            conn.execute("ALTER TABLE bottles ADD COLUMN capture_ai_json TEXT")
        if not _column_exists(conn, 'processing_bottle_matches', 'master_capture_ai_json'):
            conn.execute("ALTER TABLE processing_bottle_matches ADD COLUMN master_capture_ai_json TEXT")
        if not _column_exists(conn, 'processing_bottle_matches', 'observed_capture_ai_json'):
            conn.execute("ALTER TABLE processing_bottle_matches ADD COLUMN observed_capture_ai_json TEXT")
        if not _column_exists(conn, 'processing_bottle_matches', 'capture_ai_match_json'):
            conn.execute("ALTER TABLE processing_bottle_matches ADD COLUMN capture_ai_match_json TEXT")
        conn.commit()


def insert_bottle(data: Dict) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute("""
        INSERT INTO bottles
        (brand, product_name, sku_code, quantity_ml, color, barcode, notes,
         signature_json, tolerances_json, weights_json, image_assets_json, capture_ai_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("brand"),
            data.get("product_name"),
            data.get("sku_code", ""),
            data.get("quantity_ml") or None,
            data.get("color", ""),
            data.get("barcode", ""),
            data.get("notes", ""),
            json.dumps(data.get("signature", {})),
            json.dumps(data.get("tolerances", {})),
            json.dumps(data.get("weights", {})),
            json.dumps(data.get("image_assets", {})),
            json.dumps(data.get("capture_ai", {}), default=str),
        ))
        conn.commit()
        return int(cur.lastrowid)


def update_bottle_assets(bottle_id: int, image_assets: Dict) -> None:
    init_db()
    with get_conn() as conn:
        conn.execute("UPDATE bottles SET image_assets_json = ? WHERE id = ?", (json.dumps(image_assets or {}), bottle_id))
        conn.commit()


def update_bottle_capture_ai(bottle_id: int, capture_ai: Dict) -> None:
    init_db()
    with get_conn() as conn:
        conn.execute("UPDATE bottles SET capture_ai_json = ? WHERE id = ?", (json.dumps(capture_ai or {}, default=str), bottle_id))
        conn.commit()



def list_bottles() -> List[Dict]:
    init_db()
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM bottles ORDER BY id DESC").fetchall()
    return [_row_to_dict(row) for row in rows]


def get_bottle(bottle_id: int) -> Optional[Dict]:
    init_db()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM bottles WHERE id = ?", (bottle_id,)).fetchone()
    return _row_to_dict(row) if row else None


def delete_bottle(bottle_id: int) -> bool:
    init_db()
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM bottles WHERE id = ?", (bottle_id,))
        conn.commit()
        return cur.rowcount > 0


def insert_log(event_type: str, status: str, message: str = "", request: Dict = None, response: Dict = None) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute("""
        INSERT INTO audit_logs
        (event_type, status, message, request_json, response_json)
        VALUES (?, ?, ?, ?, ?)
        """, (
            event_type,
            status,
            message,
            json.dumps(request or {}, default=str),
            json.dumps(response or {}, default=str),
        ))
        conn.commit()
        return int(cur.lastrowid)


def list_logs(limit: int = 200) -> List[Dict]:
    init_db()
    limit = max(1, min(int(limit or 200), 1000))
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [_log_to_dict(row) for row in rows]


def clear_logs() -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM audit_logs")
        conn.commit()
        return cur.rowcount


def insert_processing_match(data: Dict) -> str:
    init_db()
    with get_conn() as conn:
        conn.execute("""
        INSERT INTO processing_bottle_matches
        (processing_match_id, bottle_id, brand, product_name, decision, score_percent,
         compared_parameters, no_match_reasons_json, request_json, observed_signature_json,
         gate_results_json, parameter_details_json, full_result_json, visual_assets_json,
         master_capture_ai_json, observed_capture_ai_json, capture_ai_match_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("processing_match_id"),
            data.get("bottle_id"),
            data.get("brand"),
            data.get("product_name"),
            data.get("decision"),
            data.get("score_percent"),
            data.get("compared_parameters"),
            json.dumps(data.get("no_match_reasons", []), default=str),
            json.dumps(data.get("request", {}), default=str),
            json.dumps(data.get("observed_signature", {}), default=str),
            json.dumps(data.get("gate_results", {}), default=str),
            json.dumps(data.get("parameter_details", []), default=str),
            json.dumps(data.get("full_result", {}), default=str),
            json.dumps(data.get("visual_assets", {}), default=str),
            json.dumps(data.get("master_capture_ai", {}), default=str),
            json.dumps(data.get("observed_capture_ai", {}), default=str),
            json.dumps(data.get("capture_ai_match", {}), default=str),
        ))
        conn.commit()
    return str(data.get("processing_match_id"))


def list_processing_matches(limit: int = 200) -> List[Dict]:
    init_db()
    limit = max(1, min(int(limit or 200), 1000))
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM processing_bottle_matches ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [_processing_match_to_dict(row) for row in rows]


def get_processing_match(processing_match_id: str) -> Optional[Dict]:
    init_db()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM processing_bottle_matches WHERE processing_match_id = ?", (processing_match_id,)).fetchone()
    return _processing_match_to_dict(row) if row else None


def _has_column(row, column: str) -> bool:
    try:
        return column in row.keys()
    except Exception:
        return False


def _json_or_empty(value, fallback):
    try:
        return json.loads(value or fallback)
    except Exception:
        return json.loads(fallback)


def _row_to_dict(row) -> Dict:
    image_assets_raw = row["image_assets_json"] if _has_column(row, "image_assets_json") else "{}"
    capture_ai_raw = row["capture_ai_json"] if _has_column(row, "capture_ai_json") else "{}"
    return {
        "id": row["id"],
        "brand": row["brand"],
        "product_name": row["product_name"],
        "sku_code": row["sku_code"],
        "quantity_ml": row["quantity_ml"],
        "color": row["color"],
        "barcode": row["barcode"],
        "notes": row["notes"],
        "signature": json.loads(row["signature_json"] or "{}"),
        "tolerances": json.loads(row["tolerances_json"] or "{}"),
        "weights": json.loads(row["weights_json"] or "{}"),
        "image_assets": _json_or_empty(image_assets_raw, "{}"),
        "capture_ai": _json_or_empty(capture_ai_raw, "{}"),
        "created_at": row["created_at"],
    }


def _log_to_dict(row) -> Dict:
    return {
        "id": row["id"],
        "event_type": row["event_type"],
        "status": row["status"],
        "message": row["message"],
        "request": json.loads(row["request_json"] or "{}"),
        "response": json.loads(row["response_json"] or "{}"),
        "created_at": row["created_at"],
    }


def _processing_match_to_dict(row) -> Dict:
    master_capture_ai_raw = row["master_capture_ai_json"] if _has_column(row, "master_capture_ai_json") else "{}"
    observed_capture_ai_raw = row["observed_capture_ai_json"] if _has_column(row, "observed_capture_ai_json") else "{}"
    capture_ai_match_raw = row["capture_ai_match_json"] if _has_column(row, "capture_ai_match_json") else "{}"
    return {
        "id": row["id"],
        "processing_match_id": row["processing_match_id"],
        "bottle_id": row["bottle_id"],
        "brand": row["brand"],
        "product_name": row["product_name"],
        "decision": row["decision"],
        "score_percent": row["score_percent"],
        "compared_parameters": row["compared_parameters"],
        "no_match_reasons": json.loads(row["no_match_reasons_json"] or "[]"),
        "request": json.loads(row["request_json"] or "{}"),
        "observed_signature": json.loads(row["observed_signature_json"] or "{}"),
        "gate_results": json.loads(row["gate_results_json"] or "{}"),
        "parameter_details": json.loads(row["parameter_details_json"] or "[]"),
        "full_result": json.loads(row["full_result_json"] or "{}"),
        "visual_assets": json.loads(row["visual_assets_json"] or "{}"),
        "master_capture_ai": _json_or_empty(master_capture_ai_raw, "{}"),
        "observed_capture_ai": _json_or_empty(observed_capture_ai_raw, "{}"),
        "capture_ai_match": _json_or_empty(capture_ai_match_raw, "{}"),
        "created_at": row["created_at"],
    }
