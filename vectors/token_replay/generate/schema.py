"""
schema.py — Vector #16 (Agentic Token Replay / Agent Pay Abuse)

Defines the synthetic session/token-event schema from §3.2 of the design doc,
plus the realistic value pools used by generator.py to build a legitimate
population before deriving attacks from it (§3.1, "clone and corrupt").

Nothing in this file simulates fraud logic — it's pure data/config.
"""

import hashlib
import random

# ---------------------------------------------------------------------------
# Value pools — kept small and realistic rather than exhaustive. Each pool
# models a real dimension of the Agent Pay trust chain (§2.2).
# ---------------------------------------------------------------------------

# (agent_id, developer_id) pairs — a developer entity KYAs once (§2.2, step 1)
# and can run multiple agent products under that one registration.
AGENTS = [
    ("agent_openai_shopgpt",     "dev_openai"),
    ("agent_msft_copilot_pay",   "dev_microsoft"),
    ("agent_perplexity_comm",    "dev_perplexity"),
    ("agent_amazon_rufus",       "dev_amazon"),
    ("agent_manus_auto",         "dev_manus_inc"),
    ("agent_ibm_watsonx_pay",    "dev_ibm"),
    ("agent_braintree_flow",     "dev_braintree_partner"),
]

MERCHANT_CATEGORIES = [
    "electronics", "grocery", "travel", "subscription",
    "apparel", "home_goods", "dining", "entertainment",
]

# A pool of concrete merchants per category (id, category) — enough variety
# that "different merchant, same category" and "different category entirely"
# are both representable (needed for T2's context_hash mismatch).
MERCHANTS = [
    ("merch_bestbuy",       "electronics"),
    ("merch_newegg",        "electronics"),
    ("merch_wholefoods",    "grocery"),
    ("merch_instacart",     "grocery"),
    ("merch_expedia",       "travel"),
    ("merch_airbnb",        "travel"),
    ("merch_netflix",       "subscription"),
    ("merch_spotify",       "subscription"),
    ("merch_zara",          "apparel"),
    ("merch_uniqlo",        "apparel"),
    ("merch_wayfair",       "home_goods"),
    ("merch_ikea",          "home_goods"),
    ("merch_doordash",      "dining"),
    ("merch_ubereats",      "dining"),
    ("merch_steam",         "entertainment"),
    ("merch_ticketmaster",  "entertainment"),
]

CHANNELS = ["agent-web", "agent-app", "agent-to-agent"]

CURRENCIES = ["USD", "USD", "USD", "EUR", "GBP", "INR"]  # weighted toward USD

# Rough (lat, lon, label) anchors used for geo/impossible-travel features.
# Not real user data — just plausible city centroids for distance math.
GEO_ANCHORS = [
    (40.7128, -74.0060, "New York,US"),
    (37.7749, -122.4194, "San Francisco,US"),
    (51.5074, -0.1278, "London,GB"),
    (48.8566, 2.3522, "Paris,FR"),
    (28.6139, 77.2090, "New Delhi,IN"),
    (19.0760, 72.8777, "Mumbai,IN"),
    (1.3521, 103.8198, "Singapore,SG"),
    (35.6762, 139.6503, "Tokyo,JP"),
    (-33.8688, 151.2093, "Sydney,AU"),
    (52.5200, 13.4050, "Berlin,DE"),
]

CONSENT_TYPES = ["single-use", "recurring"]

# Column order for the output dataset — mirrors Table 5 in the design doc.
COLUMNS = [
    "session_id", "event_id",
    "agent_id", "developer_id",
    "consent_id", "consent_type", "max_amount", "allowed_merchant_categories", "time_window_start", "time_window_end",
    "token_id", "nonce",
    "task_id",
    "token_context_hash",  # Hctx bound at issuance (task_id/agent_id/merchant_id/scope the token was minted for)
    "event_context_hash",  # Hctx recomputed from THIS event's actual task_id/merchant_id/scope
    "issued_at", "used_at",
    "merchant_id", "merchant_category",
    "amount", "currency",
    "device_fingerprint",
    "ip_address", "geo_label", "geo_lat", "geo_lon",
    "channel",
    "label",
    "drift_profile",  # ground-truth difficulty tier for T1/T3/T4 (see generator.pick_drift_profile) -- EVALUATION ONLY, never a model feature
    "pair_id",  # links a legitimate base row to the attack/retry row derived from it (traceability, not a model feature)
]


def compute_context_hash(task_id: str, agent_id: str, merchant_id: str, scope: str) -> str:
    """
    Hctx = SHA256(task_id || agent_id || merchant_id || scope)

    Mirrors the eBay/AP2 paper's own binding formula (arXiv:2602.06345) exactly,
    per §3.2, so this synthetic data is structurally compatible with a reference
    ZTRV-style verifier with no translation layer.
    """
    raw = f"{task_id}||{agent_id}||{merchant_id}||{scope}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def random_device_fingerprint(rng: random.Random) -> str:
    """Synthetic device fingerprint."""
    return "dev_" + "".join(rng.choices("0123456789abcdef", k=12))


def random_ip(rng: random.Random) -> str:
    """Synthetic IPv4 address."""
    return f"{rng.randint(1,223)}.{rng.randint(0,255)}.{rng.randint(0,255)}.{rng.randint(1,254)}"
