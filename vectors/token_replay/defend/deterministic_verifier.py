"""
deterministic_verifier.py — Layer 1 (§4.1)

A reference reimplementation of the eBay/AP2 paper's Zero-Trust Runtime
Verifier logic (arXiv:2602.06345, Algorithm 1): context-hash binding plus a
consume-once nonce registry. This is the FLOOR, not the contribution (§4.1) —
it exists so Layer 2's added value can be measured against a real, published,
working defence rather than a strawman.

Two checks, both must pass for ACCEPT:

  1. Context Binder — event_context_hash must match token_context_hash.
     A mismatch means the charge landed on a different merchant/task than the
     token was scoped for. Time-independent: catches T2 regardless of when
     the replay happens.

  2. Nonce Registry — consume-once, SLIDING WINDOW (not permanent memory).
     - Nonce never seen (or its earlier entry has expired past NONCE_TTL) ->
       treated as a fresh use -> accept, register it.
     - Nonce seen, still within TTL, same device+IP, reused within a few
       seconds -> idempotent duplicate (ordinary network retry) -> accept,
       don't re-register.
     - Nonce seen, still within TTL, anything else different -> genuine
       reuse -> reject.

  This TTL behaviour is what makes T1 (replayed in minutes) catchable here
  while T3/T4 (replayed hours/days later, after the window has slid past)
  are NOT caught here -- they fall through to Layer 2 by design (§4.2, Table 7).
"""

from datetime import datetime, timedelta


DEFAULT_NONCE_TTL_MINUTES = 60      # sliding window: how long a nonce is "remembered"
DEFAULT_DUPLICATE_WINDOW_SECONDS = 60  # how close in time + same device/IP counts as an idempotent retry
# (widened from 10s to match generate/generator.py's legitimate_retry range of 1-60s;
# keep these two in sync -- see derive_legitimate_retry in generator.py)


class NonceRegistry:
    """
    In-memory nonce store with sliding-window eviction, per §4.1.
    Keyed by nonce -> {first_used_at, last_used_at, device_fingerprint, ip_address}.
    """

    def __init__(self, ttl_minutes=DEFAULT_NONCE_TTL_MINUTES,
                 duplicate_window_seconds=DEFAULT_DUPLICATE_WINDOW_SECONDS):
        self.ttl_minutes = ttl_minutes
        self.duplicate_window_seconds = duplicate_window_seconds
        self._store = {}

    def check(self, nonce, used_at, device_fingerprint, ip_address):
        """
        Returns one of: "ACCEPT_FRESH", "ACCEPT_DUPLICATE", "REJECT_NONCE_REUSE"
        and registers/updates the entry as a side effect.
        """
        entry = self._store.get(nonce)

        if entry is None:
            self._store[nonce] = {
                "first_used_at": used_at, "last_used_at": used_at,
                "device_fingerprint": device_fingerprint, "ip_address": ip_address,
            }
            return "ACCEPT_FRESH"

        elapsed_since_first = (used_at - entry["first_used_at"]).total_seconds() / 60.0

        if elapsed_since_first > self.ttl_minutes:
            # Sliding window has moved past this nonce's original use -- treated
            # as a fresh event. This is the deliberate gap T3/T4 exploit (§4.2).
            self._store[nonce] = {
                "first_used_at": used_at, "last_used_at": used_at,
                "device_fingerprint": device_fingerprint, "ip_address": ip_address,
            }
            return "ACCEPT_FRESH"

        same_device = device_fingerprint == entry["device_fingerprint"]
        same_ip = ip_address == entry["ip_address"]
        seconds_since_last = (used_at - entry["last_used_at"]).total_seconds()

        if same_device and same_ip and 0 <= seconds_since_last <= self.duplicate_window_seconds:
            entry["last_used_at"] = used_at
            return "ACCEPT_DUPLICATE"

        # Reuse within the TTL window, but not an idempotent duplicate -> genuine replay.
        entry["last_used_at"] = used_at
        return "REJECT_NONCE_REUSE"


def context_check(token_context_hash: str, event_context_hash: str) -> bool:
    """True if the event's actual context matches what the token was bound to."""
    return token_context_hash == event_context_hash


def verify_event(row: dict, registry: NonceRegistry):
    """
    Runs both Layer-1 checks against a single event row (a dict with the
    fields produced by generate/generator.py).

    Returns a dict: {"decision": "ACCEPT"|"REJECT", "reason": str, "nonce_status": str}
    """
    used_at = datetime.fromisoformat(row["used_at"])

    ctx_ok = context_check(row["token_context_hash"], row["event_context_hash"])
    nonce_status = registry.check(
        nonce=row["nonce"],
        used_at=used_at,
        device_fingerprint=row["device_fingerprint"],
        ip_address=row["ip_address"],
    )

    if not ctx_ok:
        # Context mismatch is rejected regardless of nonce status.
        return {"decision": "REJECT", "reason": "context_hash_mismatch", "nonce_status": nonce_status}

    if nonce_status == "REJECT_NONCE_REUSE":
        return {"decision": "REJECT", "reason": "nonce_reuse", "nonce_status": nonce_status}

    return {"decision": "ACCEPT", "reason": "ok", "nonce_status": nonce_status}
