import numpy as np
import pandas as pd


# ============================================================
# DOMAIN CONSTRAINTS
# ============================================================

def apply_domain_constraints(df):
    """
    Apply business/domain constraints to generated merchant data.

    Returns
    -------
    pd.DataFrame
        Cleaned candidate samples.
    """

    data = df.copy()

    original_count = len(data)

    # ========================================================
    # REMOVE NaN / INF
    # ========================================================

    data = data.replace(
        [np.inf, -np.inf],
        np.nan
    )

    data = data.dropna()

    # ========================================================
    # OWNER AGE
    # ========================================================

    if "owner_age" in data.columns:
        data["owner_age"] = (
            pd.to_numeric(
                data["owner_age"],
                errors="coerce"
            )
            .clip(lower=18, upper=100)
            .round()
        )

    # ========================================================
    # CLAIMED REVENUE DECILE
    #
    # In your dataset this behaves as a normalized numerical
    # value rather than a strict integer 0-9.
    # ========================================================

    if "claimed_revenue_decile" in data.columns:
        data["claimed_revenue_decile"] = (
            pd.to_numeric(
                data["claimed_revenue_decile"],
                errors="coerce"
            )
            .clip(lower=0, upper=1)
        )

    # ========================================================
    # BUSINESS CREDIT SCORE
    # ========================================================

    if "business_credit_score" in data.columns:
        data["business_credit_score"] = (
            pd.to_numeric(
                data["business_credit_score"],
                errors="coerce"
            )
            .clip(lower=0, upper=1000)
            .round()
        )

    # ========================================================
    # RATIO FEATURES: [0, 1]
    # ========================================================

    ratio_columns = [
        "name_email_similarity",
        "repeat_customer_ratio",
        "large_txn_spike_ratio",
        "refund_ratio",
    ]

    for col in ratio_columns:
        if col in data.columns:
            data[col] = (
                pd.to_numeric(
                    data[col],
                    errors="coerce"
                )
                .clip(lower=0, upper=1)
            )

    # ========================================================
    # BINARY FEATURES
    # ========================================================

    binary_columns = [
        "cross_border_registration",
        "uses_free_email_domain",
    ]

    for col in binary_columns:
        if col in data.columns:

            values = pd.to_numeric(
                data[col],
                errors="coerce"
            )

            # Convert to nearest binary value.
            data[col] = (
                values >= 0.5
            ).astype(int)

    # ========================================================
    # NON-NEGATIVE FEATURES
    # ========================================================

    non_negative_columns = [
        "business_address_tenure_months",
        "shared_device_registration_count",
        "onboarding_doc_velocity_6h",
        "onboarding_doc_velocity_24h",
        "onboarding_doc_velocity_4w",
        "requested_processing_limit",
        "onboarding_duration_days",
        "txn_count_90d",
        "avg_txn_amount",
        "unique_cardholder_count",
    ]

    for col in non_negative_columns:
        if col in data.columns:

            data[col] = (
                pd.to_numeric(
                    data[col],
                    errors="coerce"
                )
                .clip(lower=0)
            )

    # ========================================================
    # INTEGER-LIKE COUNT FEATURES
    #
    # We round only variables that represent counts.
    # ========================================================

    count_columns = [
        "shared_device_registration_count",
        "txn_count_90d",
        "unique_cardholder_count",
    ]

    for col in count_columns:
        if col in data.columns:
            data[col] = (
                data[col]
                .round()
            )

    # ========================================================
    # REMOVE ANY NEW NaNs CAUSED BY CONVERSION
    # ========================================================

    data = data.replace(
        [np.inf, -np.inf],
        np.nan
    )

    data = data.dropna()

    removed = original_count - len(data)

    print("\n[CONSTRAINTS] Domain validation complete.")
    print(
        f"[CONSTRAINTS] Input samples:  {original_count}"
    )
    print(
        f"[CONSTRAINTS] Valid samples:  {len(data)}"
    )
    print(
        f"[CONSTRAINTS] Removed samples: {removed}"
    )

    return data.reset_index(drop=True)


# ============================================================
# BASIC VALIDATION
# ============================================================

def validate_samples(df, expected_features):
    """
    Performs final structural validation before Blue Team scoring.
    """

    missing_columns = [
        col for col in expected_features
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required features:\n"
            f"{missing_columns}"
        )

    data = df[expected_features].copy()

    if data.isna().any().any():
        raise ValueError(
            "NaN values found after domain processing."
        )

    numeric_data = data.select_dtypes(
        include=[np.number]
    )

    if np.isinf(numeric_data.to_numpy()).any():
        raise ValueError(
            "Infinite values found after domain processing."
        )

    return data