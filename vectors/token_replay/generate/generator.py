"""
generator.py — Vector #16 (Agentic Token Replay / Agent Pay Abuse)

Implements §3.1-3.3 of the design doc:
  1. Build a realistic LEGITIMATE population first (never sample fraud independently).
  2. Clone a sampled subset of legitimate sessions and corrupt exactly the fields
     that a legitimate reuse should never break, per attack sub-class (Table 6).
  3. Keep fraud a small minority of total volume (realistic base rates), and
     include a "legitimate_retry" hard negative so the classifier has to learn
     where the real decision boundary sits, not just spot obvious outliers.

Run: python generator.py
Output: ../data/sessions.csv
"""

import csv
import math
import random
import uuid
from datetime import datetime, timedelta, timezone

import schema

# ---------------------------------------------------------------------------
# Config — deliberately small for this first pass; scale later by raising
# N_BASE (and, if needed, moving the CSV write to a chunked/parquet writer).
# ---------------------------------------------------------------------------
SEED = 42
N_BASE = 25000         # legitimate base sessions generated first (scaled up from 3,000 --
                       # see PROGRESS.md next-steps #3; thin per-tier counts, e.g.
                       # full_hard n=3-12, made some drift-profile splits hard to trust)
FRAUD_RATE_TARGET = 0.07   # ~7% of final rows are T1-T4 fraud (realistic minority)
RETRY_RATE_TARGET = 0.04   # ~4% of final rows are legitimate_retry hard negatives

# Split of the fraud budget across T1/T2/T3/T4 (must sum to 1.0)
FRAUD_MIX = {"T1": 0.35, "T2": 0.30, "T3": 0.20, "T4": 0.15}

# Fraction of legitimate sessions where the agent uses the token LATE in its
# consent window (hours to days after issuance) rather than immediately.
# Without this, "time since issuance" alone perfectly separates legitimate
# from T3/T4 in the synthetic data -- an artifact of the generator, not a
# real fraud signal -- and Layer 2 learns to key off it instead of the
# device/IP/geo drift signals it's actually supposed to use (Table 7).
LATE_USE_PROB = 0.35

OUT_PATH = "../data/sessions.csv"


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lon points, in kilometres."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def new_id(prefix):
    """Fresh random hex identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def make_legitimate_base(rng: random.Random, n: int):
    """Builds n independent, ordinary legitimate sessions."""
    rows = []
    base_time = datetime(2026, 8, 1, tzinfo=timezone.utc)

    for _ in range(n):
        agent_id, developer_id = rng.choice(schema.AGENTS)
        merchant_id, merchant_category = rng.choice(schema.MERCHANTS)

        consent_id = new_id("consent")
        consent_type = rng.choices(schema.CONSENT_TYPES, weights=[0.6, 0.4])[0]
        max_amount = round(rng.uniform(20, 1500), 2)
        # allowed categories: usually the session's own category, sometimes a couple more
        allowed_categories = {merchant_category}
        if rng.random() < 0.3:
            allowed_categories.add(rng.choice(schema.MERCHANT_CATEGORIES))
        allowed_categories = sorted(allowed_categories)

        window_start = base_time + timedelta(days=rng.randint(0, 20), hours=rng.randint(0, 23))
        window_end = window_start + timedelta(hours=rng.choice([1, 6, 24, 72, 168]))

        token_id = new_id("tok")
        nonce = uuid.uuid4().hex
        task_id = new_id("task")

        scope_str = f"{max_amount}|{','.join(allowed_categories)}|{consent_type}"
        token_ctx_hash = schema.compute_context_hash(task_id, agent_id, merchant_id, scope_str)
        event_ctx_hash = token_ctx_hash  # legitimate first use: event matches what the token was bound for

        issued_at = window_start + timedelta(minutes=rng.randint(1, 30))

        # Realistic usage timing: most legitimate uses happen quickly, but a
        # meaningful minority happen late in the consent window (an agent
        # acting on a multi-day or recurring mandate doesn't necessarily fire
        # within seconds of issuance). This deliberately overlaps with the
        # T1 (minutes) and T3/T4 (hours-days) delay ranges so the classifier
        # can't use elapsed time alone as a shortcut -- it has to learn the
        # device/IP/geo drift signals that actually distinguish genuine late
        # use from a leaked-and-replayed token.
        window_seconds = max((window_end - issued_at).total_seconds(), 60)
        if rng.random() < LATE_USE_PROB:
            used_at = issued_at + timedelta(seconds=rng.uniform(600, window_seconds))
        else:
            used_at = issued_at + timedelta(seconds=rng.randint(5, 600))

        amount = round(min(max_amount, max(1, rng.uniform(5, max_amount))), 2)
        currency = rng.choice(schema.CURRENCIES)

        device_fp = schema.random_device_fingerprint(rng)
        ip = schema.random_ip(rng)
        lat, lon, geo_label = rng.choice(schema.GEO_ANCHORS)

        channel = rng.choice(schema.CHANNELS)

        session_id = new_id("sess")
        event_id = new_id("evt")

        row = {
            "session_id": session_id, "event_id": event_id,
            "agent_id": agent_id, "developer_id": developer_id,
            "consent_id": consent_id, "consent_type": consent_type,
            "max_amount": max_amount, "allowed_merchant_categories": ";".join(allowed_categories),
            "time_window_start": window_start.isoformat(), "time_window_end": window_end.isoformat(),
            "token_id": token_id, "nonce": nonce,
            "task_id": task_id,
            "token_context_hash": token_ctx_hash, "event_context_hash": event_ctx_hash,
            "issued_at": issued_at.isoformat(), "used_at": used_at.isoformat(),
            "merchant_id": merchant_id, "merchant_category": merchant_category,
            "amount": amount, "currency": currency,
            "device_fingerprint": device_fp,
            "ip_address": ip, "geo_label": geo_label, "geo_lat": lat, "geo_lon": lon,
            "channel": channel,
            "label": "legitimate",
            "drift_profile": "n/a",
            "pair_id": session_id,  # a legitimate base row is its own pair root
            # kept only in-memory for derivation, stripped before CSV write:
            "_scope_str": scope_str,
        }
        rows.append(row)
    return rows


def pick_drift_profile(rng: random.Random):
    """
    Chooses how much of the device/IP/geo fingerprint an attacker preserves
    during replay. Real attackers don't always trip every signal at once --
    spoofed fingerprints, shared IP ranges/VPNs, and corporate NAT all let a
    replay partially blend in. This is what turns T1/T3/T4 from a trivially
    separable class into one with a genuine difficulty spread (§3.4).

    Returns (device_same, ip_same, geo_same, profile_name).
    geo is tied to ip_same: if the IP is preserved, the location should be
    too (an IP maps to a place -- keeping one but not the other is internally
    inconsistent synthetic data).
    """
    roll = rng.random()
    if roll < 0.50:
        return False, False, False, "obvious"          # full drift -- easy case
    elif roll < 0.70:
        return True, False, False, "device_spoofed"    # fingerprint faked, network genuinely different
    elif roll < 0.85:
        return False, True, True, "same_network"        # different device, same network/location (e.g. shared NAT)
    else:
        return True, True, True, "full_hard"             # fingerprint faked AND same network -- near-invisible
                                                           # via device/IP/geo signals; the genuinely hard near-miss


def derive_T1(base_row, rng):
    """
    Same-context replay (temporal violation): token reused within its validity
    window. Difficulty varies via pick_drift_profile -- from "different device,
    different country, impossible travel" (obvious) down to "same device
    signature, same network" (full_hard), per Table 6 and §3.4.
    """
    r = dict(base_row)
    used_at1 = datetime.fromisoformat(base_row["used_at"])

    delta_seconds = rng.randint(10, 2700)  # 10s to 45min; overlaps legitimate_retry's range by design
    used_at2 = used_at1 + timedelta(seconds=delta_seconds)

    device_same, ip_same, geo_same, profile = pick_drift_profile(rng)

    device_fp = base_row["device_fingerprint"] if device_same else schema.random_device_fingerprint(rng)
    ip = base_row["ip_address"] if ip_same else schema.random_ip(rng)
    if geo_same:
        lat2, lon2, geo_label2 = base_row["geo_lat"], base_row["geo_lon"], base_row["geo_label"]
    else:
        lat2, lon2, geo_label2 = rng.choice([g for g in schema.GEO_ANCHORS if g[2] != base_row["geo_label"]])

    dist_km = haversine_km(base_row["geo_lat"], base_row["geo_lon"], lat2, lon2)
    implied_speed_kmh = dist_km / max((delta_seconds / 3600), 1e-6)

    r.update({
        "event_id": new_id("evt"),
        "used_at": used_at2.isoformat(),
        "device_fingerprint": device_fp,
        "ip_address": ip,
        "geo_lat": lat2, "geo_lon": lon2, "geo_label": geo_label2,
        # token, task_id, merchant, scope all UNCHANGED -> context hash still matches
        "label": "T1",
        "drift_profile": profile,
        "pair_id": base_row["session_id"],
    })
    r["_implied_speed_kmh"] = implied_speed_kmh
    return r


def derive_T2(base_row, rng):
    """
    Cross-context replay (spatial violation): token/agent_id unchanged, but the
    charge lands on a different merchant/task than the token's own scope ->
    event_context_hash no longer matches token_context_hash (Table 6).
    """
    r = dict(base_row)
    other_merchant_id, other_category = rng.choice(
        [m for m in schema.MERCHANTS if m[0] != base_row["merchant_id"]]
    )
    new_task_id = new_id("task")
    new_event_hash = schema.compute_context_hash(
        new_task_id, base_row["agent_id"], other_merchant_id, base_row["_scope_str"]
    )
    used_at2 = datetime.fromisoformat(base_row["used_at"]) + timedelta(minutes=rng.randint(1, 120))

    r.update({
        "event_id": new_id("evt"),
        "task_id": new_task_id,
        "merchant_id": other_merchant_id, "merchant_category": other_category,
        "event_context_hash": new_event_hash,  # token_context_hash stays as originally issued -> mismatch
        "used_at": used_at2.isoformat(),
        "amount": round(rng.uniform(5, base_row["max_amount"]), 2),
        "label": "T2",
        "drift_profile": "n/a",
        "pair_id": base_row["session_id"],
    })
    return r


def derive_T3_T4(base_row, rng, sub_label):
    """
    Context-leakage-induced misuse / observability-based replay: token harvested
    from logs/traces and replayed much later. Difficulty varies via
    pick_drift_profile the same way T1 does -- a leaked token used from the
    same device/network (full_hard) is a much harder catch than one used from
    a clearly unrelated device and location (obvious), per Table 6 and §3.4.
    """
    r = dict(base_row)
    used_at1 = datetime.fromisoformat(base_row["used_at"])
    # Leakage-based reuse: longer, more variable delay than T1's quick replay --
    # models "harvested from a log/trace and used later", not a live race condition.
    delay_hours = rng.uniform(2, 96)
    used_at2 = used_at1 + timedelta(hours=delay_hours)

    device_same, ip_same, geo_same, profile = pick_drift_profile(rng)

    device_fp = base_row["device_fingerprint"] if device_same else schema.random_device_fingerprint(rng)
    ip = base_row["ip_address"] if ip_same else schema.random_ip(rng)
    if geo_same:
        lat2, lon2, geo_label2 = base_row["geo_lat"], base_row["geo_lon"], base_row["geo_label"]
    else:
        lat2, lon2, geo_label2 = rng.choice([g for g in schema.GEO_ANCHORS if g[2] != base_row["geo_label"]])

    r.update({
        "event_id": new_id("evt"),
        "used_at": used_at2.isoformat(),
        "device_fingerprint": device_fp,
        "ip_address": ip,
        "geo_lat": lat2, "geo_lon": lon2, "geo_label": geo_label2,
        # token, task_id, merchant, scope unchanged -> context hash still matches (this is what
        # makes T3/T4 harder than T2: no deterministic mismatch signal, only device/time drift).
        "label": sub_label,  # "T3" or "T4"
        "drift_profile": profile,
        "pair_id": base_row["session_id"],
    })
    return r


def derive_legitimate_retry(base_row, rng):
    """
    Hard negative: an ordinary network-timeout retry. Same token, same merchant,
    same device, near-identical timestamp -- nothing meaningful changed. The
    classifier must learn NOT to flag this even though a token is technically
    being "reused" (Table 6).
    """
    r = dict(base_row)
    used_at1 = datetime.fromisoformat(base_row["used_at"])
    # Widened from a tight 1-8s to 1-60s -- ordinary retry/timeout behaviour is
    # not always instant, and this range needs to genuinely overlap with T1's
    # low end (see derive_T1) so the classifier can't use timing alone.
    used_at2 = used_at1 + timedelta(seconds=rng.randint(1, 60))

    r.update({
        "event_id": new_id("evt"),
        "used_at": used_at2.isoformat(),
        # device_fingerprint, ip_address, geo, merchant, token all UNCHANGED
        "label": "legitimate_retry",
        "drift_profile": "n/a",
        "pair_id": base_row["session_id"],
    })
    return r


def _is_late_use(row, threshold_hours=24.0):
    """
    True if this legitimate base row's first use happened more than
    threshold_hours after issuance (i.e. it landed in the LATE_USE_PROB
    branch of make_legitimate_base).
    """
    issued_at = datetime.fromisoformat(row["issued_at"])
    used_at = datetime.fromisoformat(row["used_at"])
    return (used_at - issued_at).total_seconds() / 3600.0 > threshold_hours


# Feedback-loop hardening (§6), added after mining a real Layer-2 false
# negative: a T1/device_spoofed replay derived from a late-use legitimate
# base row scored proba=0.0000 despite an 18,735 km/h implied travel speed,
# because seconds_since_issued (~5.4 days, indistinguishable from an
# ordinary late legitimate use) dominated the model's decision and
# implied_speed_kmh got 0 feature importance -- the signal existed in the
# data but wasn't represented often enough for the model to learn to weight
# it. This forces a minimum fraction of T1/T3/T4 attacks to be derived
# specifically from late-use base rows, so that interaction gets enough
# training exposure. See docs/feedback_loop_log.md for the full mining
# writeup and retrain results.
LATE_USE_HARD_CASE_FRACTION = 0.40


def build_dataset(seed=SEED, n_base=N_BASE):
    """Generate the full session set: legitimate traffic plus each attack sub-class."""
    rng = random.Random(seed)
    base_rows = make_legitimate_base(rng, n_base)

    n_fraud_total = int(round(n_base * FRAUD_RATE_TARGET))
    n_retry_total = int(round(n_base * RETRY_RATE_TARGET))

    fraud_counts = {k: int(round(n_fraud_total * v)) for k, v in FRAUD_MIX.items()}

    pool = base_rows[:]  # rows eligible to have a derived event built from them
    rng.shuffle(pool)

    late_pool = [r for r in pool if _is_late_use(r)]
    other_pool = [r for r in pool if not _is_late_use(r)]
    rng.shuffle(late_pool)
    rng.shuffle(other_pool)

    derived_rows = []
    late_idx = 0
    other_idx = 0

    def take_source(force_late):
        nonlocal late_idx, other_idx
        if force_late and late_idx < len(late_pool):
            src = late_pool[late_idx]
            late_idx += 1
            return src
        if other_idx < len(other_pool):
            src = other_pool[other_idx]
            other_idx += 1
            return src
        if late_idx < len(late_pool):
            src = late_pool[late_idx]
            late_idx += 1
            return src
        return None

    for sub_label, count in fraud_counts.items():
        n_forced_late = int(round(count * LATE_USE_HARD_CASE_FRACTION)) if sub_label != "T2" else 0
        for i in range(count):
            src = take_source(force_late=(i < n_forced_late))
            if src is None:
                break
            if sub_label == "T1":
                derived_rows.append(derive_T1(src, rng))
            elif sub_label == "T2":
                derived_rows.append(derive_T2(src, rng))
            else:
                derived_rows.append(derive_T3_T4(src, rng, sub_label))

    for _ in range(n_retry_total):
        src = take_source(force_late=False)
        if src is None:
            break
        derived_rows.append(derive_legitimate_retry(src, rng))

    all_rows = base_rows + derived_rows
    rng.shuffle(all_rows)
    return all_rows


def write_csv(rows, path):
    """Write sessions to disk."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=schema.COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def print_sanity_report(rows):
    """Print class balance and drift spread, so bad generations are caught early."""
    from collections import Counter
    labels = Counter(r["label"] for r in rows)
    total = len(rows)
    print(f"Total rows: {total}")
    for label, count in sorted(labels.items(), key=lambda x: -x[1]):
        print(f"  {label:18s} {count:6d}  ({count/total:5.1%})")

    fraud_labels = {"T1", "T2", "T3", "T4"}
    fraud_count = sum(c for l, c in labels.items() if l in fraud_labels)
    print(f"\nOverall fraud rate (T1-T4): {fraud_count/total:.2%}")
    print(f"Hard-negative (legitimate_retry) rate: {labels.get('legitimate_retry',0)/total:.2%}")

    # Sanity: T2 should show event/token context hash mismatch; others should not.
    t2_rows = [r for r in rows if r["label"] == "T2"]
    t2_mismatch = sum(1 for r in t2_rows if r["event_context_hash"] != r["token_context_hash"])
    print(f"\nT2 rows with context-hash mismatch: {t2_mismatch}/{len(t2_rows)} (should equal total T2 rows)")

    non_t2 = [r for r in rows if r["label"] != "T2"]
    non_t2_match = sum(1 for r in non_t2 if r["event_context_hash"] == r["token_context_hash"])
    print(f"Non-T2 rows with matching context hash: {non_t2_match}/{len(non_t2)} (should equal total non-T2 rows)")


if __name__ == "__main__":
    rows = build_dataset()
    write_csv(rows, OUT_PATH)
    print(f"Wrote {len(rows)} rows to {OUT_PATH}\n")
    print_sanity_report(rows)
