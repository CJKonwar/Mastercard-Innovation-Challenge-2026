"""
features.py — Layer 2 feature engineering (§4.1, Table 7)

Builds the feature set the ML risk scorer trains on. Two kinds of features:

  1. Per-nonce HISTORY features: device/IP/geo drift and elapsed time versus
     this nonce's own prior use. This is deliberately the ML analogue of what
     the Layer-1 NonceRegistry tracks -- but instead of a binary accept/reject,
     we keep the continuous signal (distance in km, implied speed, seconds
     elapsed) so the model can learn where the real decision boundary sits
     for borderline cases a hard gate can't express (§4.2).

  2. Per-event CONTEXT features: amount-to-limit ratio, time-of-day, channel,
     merchant category, whether event_context_hash matches token_context_hash
     (kept as a feature for defence-in-depth per §4.2c, even though Layer 1
     already gates on it deterministically).

IMPORTANT: raw identifiers (nonce, token_id, device_fingerprint string,
ip_address string, session_id, agent_id string, etc.) are NEVER used directly
as model features. Each nonce appears in at most two rows in this dataset, so
including the raw ID would let the model memorize identity instead of
learning the underlying pattern -- it would look flawless here and fail
completely on unseen tokens. Only derived/relative signals go into the model.
"""

import math
from collections import defaultdict
from datetime import datetime

import pandas as pd

FRAUD_LABELS = {"T1", "T2", "T3", "T4"}

# Columns actually fed to the model. Everything else is either a raw ID
# (excluded, see module docstring) or metadata kept for reporting.
MODEL_FEATURES = [
    "is_first_use",
    "seconds_since_issued",
    "seconds_since_prior_use",
    "prior_use_count",
    "device_changed",
    "ip_changed",
    "geo_distance_km",
    "implied_speed_kmh",
    "context_match",
    "amount_to_limit_ratio",
    "hour_of_day",
    "day_of_week",
    "channel",
    "merchant_category",
    "consent_type",
    "currency",
]

CATEGORICAL_FEATURES = ["channel", "merchant_category", "consent_type", "currency"]


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lon points, in kilometres."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def build_features(rows: list[dict]) -> pd.DataFrame:
    """
    rows: list of dicts as read from data/sessions.csv (csv.DictReader output,
    all values strings). Must be processed in chronological order since
    per-nonce history is stateful -- this function sorts internally, so
    callers don't need to pre-sort.
    """
    rows = sorted(rows, key=lambda r: r["used_at"])

    history = {}  # nonce -> {"first_used_at", "last_used_at", "device_fingerprint", "ip_address", "lat", "lon", "count"}
    out = []

    for r in rows:
        used_at = datetime.fromisoformat(r["used_at"])
        issued_at = datetime.fromisoformat(r["issued_at"])
        lat, lon = float(r["geo_lat"]), float(r["geo_lon"])
        nonce = r["nonce"]

        h = history.get(nonce)

        if h is None:
            is_first_use = 1
            seconds_since_prior_use = 0.0
            prior_use_count = 0
            device_changed = 0
            ip_changed = 0
            geo_distance_km = 0.0
            implied_speed_kmh = 0.0
        else:
            is_first_use = 0
            seconds_since_prior_use = max(0.0, (used_at - h["last_used_at"]).total_seconds())
            prior_use_count = h["count"]
            device_changed = int(r["device_fingerprint"] != h["device_fingerprint"])
            ip_changed = int(r["ip_address"] != h["ip_address"])
            geo_distance_km = haversine_km(h["lat"], h["lon"], lat, lon)
            hours = max(seconds_since_prior_use / 3600.0, 1e-6)
            implied_speed_kmh = geo_distance_km / hours

        seconds_since_issued = max(0.0, (used_at - issued_at).total_seconds())
        context_match = int(r["token_context_hash"] == r["event_context_hash"])
        max_amount = float(r["max_amount"])
        amount_to_limit_ratio = float(r["amount"]) / max_amount if max_amount > 0 else 0.0

        feat = {
            "event_id": r["event_id"],  # kept for joining results back, NOT a model feature
            "label": r["label"],
            "drift_profile": r.get("drift_profile", "n/a"),  # ground-truth difficulty tier, EVALUATION ONLY -- never a model feature
            "is_first_use": is_first_use,
            "seconds_since_issued": seconds_since_issued,
            "seconds_since_prior_use": seconds_since_prior_use,
            "prior_use_count": prior_use_count,
            "device_changed": device_changed,
            "ip_changed": ip_changed,
            "geo_distance_km": geo_distance_km,
            "implied_speed_kmh": implied_speed_kmh,
            "context_match": context_match,
            "amount_to_limit_ratio": amount_to_limit_ratio,
            "hour_of_day": used_at.hour,
            "day_of_week": used_at.weekday(),
            "channel": r["channel"],
            "merchant_category": r["merchant_category"],
            "consent_type": r["consent_type"],
            "currency": r["currency"],
        }
        out.append(feat)

        # update history AFTER computing features for this row
        history[nonce] = {
            "first_used_at": h["first_used_at"] if h else used_at,
            "last_used_at": used_at,
            "device_fingerprint": r["device_fingerprint"],
            "ip_address": r["ip_address"],
            "lat": lat, "lon": lon,
            "count": (h["count"] + 1) if h else 1,
        }

    df = pd.DataFrame(out)
    df["fraud"] = df["label"].isin(FRAUD_LABELS).astype(int)
    for c in CATEGORICAL_FEATURES:
        df[c] = df[c].astype("category")
    return df
