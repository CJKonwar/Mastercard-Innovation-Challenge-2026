"""
mine_failures.py — pulls Layer 2's false negatives from the held-out test
set and characterizes each one: which fields matched a legitimate pattern,
which didn't, and what probability the model assigned.

This is step 1 of the §6 feedback loop: mine -> characterize -> turn into a
new generation rule -> retrain -> confirm.

Run: python mine_failures.py
"""

import pandas as pd

from train_layer2 import train_and_evaluate
from features import MODEL_FEATURES

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 160)


def main():
    """Surface the cases the pipeline missed or scored least confidently."""
    model, df, (X_test, y_test, label_test, pred_test, proba_test) = train_and_evaluate()

    test_df = df.loc[X_test.index].copy()
    test_df["pred"] = pred_test
    test_df["proba"] = proba_test

    fn_mask = (y_test.values == 1) & (pred_test == 0)
    fn = test_df.loc[X_test.index[fn_mask]]

    print("\n" + "=" * 70)
    print(f"FALSE NEGATIVES: {len(fn)} row(s)")
    print("=" * 70)

    if len(fn) == 0:
        print("No false negatives this run/seed -- try a different random_state "
              "in train_test_split, or note this in the feedback-loop log as a "
              "clean run and mine the LOWEST-confidence true positives instead.")
        # Fall back: show the lowest-confidence correct catches, since those
        # are the closest calls the model made and still worth characterizing.
        tp_mask = (y_test.values == 1) & (pred_test == 1)
        tp = test_df.loc[X_test.index[tp_mask]].sort_values("proba").head(5)
        print("\nLowest-confidence TRUE POSITIVES (closest calls):")
        cols = ["label", "drift_profile", "proba"] + MODEL_FEATURES
        print(tp[cols].to_string(index=False))
        return

    cols = ["label", "drift_profile", "proba"] + MODEL_FEATURES
    print(fn[cols].to_string(index=False))

    print("\nCharacterization:")
    for _, row in fn.iterrows():
        print(f"\n- {row['label']} / {row['drift_profile']}, model probability={row['proba']:.4f}")
        print(f"  device_changed={row['device_changed']}  ip_changed={row['ip_changed']}  "
              f"geo_distance_km={row['geo_distance_km']:.1f}  implied_speed_kmh={row['implied_speed_kmh']:.1f}")
        print(f"  seconds_since_issued={row['seconds_since_issued']:.0f}  "
              f"seconds_since_prior_use={row['seconds_since_prior_use']:.0f}  "
              f"prior_use_count={row['prior_use_count']}")
        print(f"  amount_to_limit_ratio={row['amount_to_limit_ratio']:.3f}  "
              f"hour_of_day={row['hour_of_day']}  channel={row['channel']}")


if __name__ == "__main__":
    main()
