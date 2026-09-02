"""Feature extraction, deterministic synthetic history, and safe model inference."""
import csv
import json
from functools import lru_cache
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "seed_data"
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
MODEL_FILE = ARTIFACTS / "risk_model.joblib"
METADATA_FILE = ARTIFACTS / "risk_model_metadata.json"
SEED = 42
_PREDICTION_CACHE = {}

def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d")

def features(task, asset):
    now = datetime(2026, 9, 1)
    return {
        "asset_type": asset.get("asset_type", "Unknown"), "asset_condition": asset.get("condition", "Fair"),
        "asset_criticality": task.get("asset_criticality", asset.get("criticality", "Medium")), "asset_status": asset.get("status", "Operational"),
        "severity": task.get("severity", "Medium"), "task_type": task.get("task_type", "Inspection"), "traffic_impact": task.get("traffic_impact", "Medium"),
        "department": task.get("required_department", asset.get("department", "Unknown")), "corridor": task.get("corridor", "Unknown"),
        "duration_minutes": float(task.get("estimated_duration_minutes", 60)), "simulated_failure_signal": float(task.get("failure_probability", 0.2)),
        "days_since_maintenance": max(0, (now - parse_date(asset.get("last_maintenance", "2026-01-01"))).days),
        "days_to_next_maintenance": (parse_date(asset.get("next_maintenance", "2026-12-01")) - now).days,
        "deadline_hours": max(0, (datetime.strptime(task.get("deadline", "2026-09-10 00:00:00"), "%Y-%m-%d %H:%M:%S") - now).total_seconds() / 3600),
    }

def generate_history(tasks, assets):
    """Creates feature-correlated, noisy simulation history; never uses future outcome as input."""
    import random
    rng = random.Random(SEED); by_asset = {a["asset_id"]: a for a in assets}; rows=[]
    for task in tasks:
        asset = by_asset[task["asset_id"]]
        for observation in range(3):
            row = features(task, asset); row["observation"] = observation
            risk = .04 + .25*(asset["condition"] in ("Poor","Critical")) + .16*(task["asset_criticality"] in ("High","Critical")) + .14*(task["traffic_impact"]=="High") + .16*(task["severity"] in ("High","Critical")) + .18*float(task["failure_probability"])
            target = int(rng.random() < min(.92,max(.04,risk + rng.uniform(-.16,.16))))
            rows.append((row,target))
    return rows

@lru_cache(maxsize=1)
def load_metadata():
    return json.loads(METADATA_FILE.read_text(encoding="utf-8")) if METADATA_FILE.exists() else None

@lru_cache(maxsize=1)
def load_model():
    if not MODEL_FILE.exists(): return None
    try:
        import joblib
        return joblib.load(MODEL_FILE)
    except Exception:
        return None

def predict(task, asset):
    cache_key = task.get("task_id")
    if cache_key in _PREDICTION_CACHE: return _PREDICTION_CACHE[cache_key]
    model = load_model()
    fallback = float(task.get("failure_probability", .2))
    if not model: return fallback, False, []
    try:
        probability = float(model.predict_proba([features(task,asset)])[0][1])
        signals = [
            {"feature":"asset_condition","value":asset.get("condition"),"importance":"model signal"},
            {"feature":"asset_criticality","value":task.get("asset_criticality"),"importance":"model signal"},
            {"feature":"traffic_impact","value":task.get("traffic_impact"),"importance":"model signal"},
        ]
        result = probability, True, signals; _PREDICTION_CACHE[cache_key] = result; return result
    except Exception:
        return fallback, False, []
