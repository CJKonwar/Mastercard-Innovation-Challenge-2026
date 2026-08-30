import json
import random
from datetime import datetime

import numpy as np
import pandas as pd

from config import (
    RESULTS_DIR,
    TARGET_VALID_SAMPLES,
    GENERATION_BATCH_SIZE,
    MAX_GENERATION_ROUNDS,
    BLUE_TEAM_THRESHOLD,
    ALL_SAMPLES_PATH,
    EVADED_SAMPLES_PATH,
    DETECTED_SAMPLES_PATH,
    SUMMARY_PATH,
    RANDOM_SEED,
)

from generator import FraudGenerator

from blue_team import BlueTeamDetector

from constraints import (
    apply_domain_constraints,
    validate_samples,
)


# ============================================================
# REPRODUCIBILITY
# ============================================================

def set_seed(seed):

    """Fix every random source so a run is reproducible."""
    random.seed(seed)
    np.random.seed(seed)


# ============================================================
# BANNER
# ============================================================

def print_banner():

    """Print the run header."""
    print("\n")
    print("=" * 70)
    print("       MERCHANT FRAUD ADVERSARIAL ATTACK SIMULATION")
    print("=" * 70)

    print(
        "\nThis simulation automatically:"
    )

    print(
        "1. Generates synthetic fraud candidates using CTGAN"
    )

    print(
        "2. Applies domain and data-validity constraints"
    )

    print(
        "3. Sends valid candidates to the Final Blue Team MLP"
    )

    print(
        "4. Separates candidates into DETECTED and EVADED groups"
    )

    print("=" * 70)


# ============================================================
# GENERATE VALID SAMPLES
# ============================================================

def generate_valid_samples(
    generator,
    target_samples,
    batch_size,
    max_rounds
):

    """Generate candidates until enough pass domain validation."""
    collected_samples = []

    total_generated = 0
    total_valid = 0

    print("\n")
    print("=" * 70)
    print("GENERATING SYNTHETIC FRAUD")
    print("=" * 70)

    for round_number in range(1, max_rounds + 1):

        if total_valid >= target_samples:
            break

        remaining = target_samples - total_valid

        current_batch_size = max(
            batch_size,
            remaining
        )

        print(
            f"\nGeneration Round "
            f"{round_number}/{max_rounds}"
        )

        print(
            f"Requesting CTGAN candidates: "
            f"{current_batch_size}"
        )

        # ----------------------------------------------------
        # GENERATE
        # ----------------------------------------------------

        generated = generator.generate(
            current_batch_size
        )

        total_generated += len(generated)

        # ----------------------------------------------------
        # DOMAIN CONSTRAINTS
        # ----------------------------------------------------

        constrained = apply_domain_constraints(
            generated
        )

        # ----------------------------------------------------
        # FINAL VALIDATION
        # ----------------------------------------------------

        valid = validate_samples(
            constrained,
            generator.features
        )

        if len(valid) == 0:

            print(
                "[WARNING] No valid samples in this round."
            )

            continue

        # ----------------------------------------------------
        # KEEP ONLY REQUIRED NUMBER
        # ----------------------------------------------------

        remaining = target_samples - total_valid

        valid = valid.head(remaining)

        collected_samples.append(valid)

        total_valid += len(valid)

        print(
            f"[ROUND {round_number}] "
            f"Collected valid samples: "
            f"{total_valid}/{target_samples}"
        )

    # ========================================================
    # COMBINE
    # ========================================================

    if not collected_samples:

        raise RuntimeError(
            "\nNo valid samples could be generated."
        )

    final_samples = pd.concat(
        collected_samples,
        ignore_index=True
    )

    print("\n")
    print("=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)

    print(
        f"Total CTGAN candidates generated: "
        f"{total_generated}"
    )

    print(
        f"Total valid samples retained:     "
        f"{len(final_samples)}"
    )

    if len(final_samples) < target_samples:

        print(
            "\nWARNING:"
        )

        print(
            f"Requested {target_samples} valid samples "
            f"but only {len(final_samples)} were obtained."
        )

    return final_samples, total_generated


# ============================================================
# ATTACK SIMULATION
# ============================================================

def run_attack(
    num_samples=TARGET_VALID_SAMPLES
):

    """Generate, validate, score and split candidates into detected and evaded."""
    set_seed(RANDOM_SEED)

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print_banner()

    # ========================================================
    # LOAD MODELS
    # ========================================================

    print("\n")
    print("=" * 70)
    print("LOADING MODELS")
    print("=" * 70)

    generator = FraudGenerator()

    blue_team = BlueTeamDetector()

    # ========================================================
    # GENERATE VALID FRAUD CANDIDATES
    # ========================================================

    candidates, total_generated = (
        generate_valid_samples(
            generator=generator,
            target_samples=num_samples,
            batch_size=GENERATION_BATCH_SIZE,
            max_rounds=MAX_GENERATION_ROUNDS
        )
    )

    # ========================================================
    # BLUE TEAM SCORING
    # ========================================================

    print("\n")
    print("=" * 70)
    print("ATTACKING FINAL BLUE TEAM")
    print("=" * 70)

    print(
        f"Samples submitted: {len(candidates)}"
    )

    print(
        f"Detection threshold: "
        f"{BLUE_TEAM_THRESHOLD:.2f}"
    )

    probabilities, detected_mask = (
        blue_team.detect(
            candidates,
            threshold=BLUE_TEAM_THRESHOLD
        )
    )

    # ========================================================
    # ADD RESULTS
    # ========================================================

    results = candidates.copy()

    results["blue_team_fraud_probability"] = (
        probabilities
    )

    results["blue_team_decision"] = np.where(
        detected_mask,
        "DETECTED",
        "EVADED"
    )

    results["evaded"] = (
        ~detected_mask
    ).astype(int)

    # ========================================================
    # SPLIT RESULTS
    # ========================================================

    detected_samples = (
        results[
            results["blue_team_decision"] == "DETECTED"
        ]
        .copy()
        .reset_index(drop=True)
    )

    evaded_samples = (
        results[
            results["blue_team_decision"] == "EVADED"
        ]
        .copy()
        .reset_index(drop=True)
    )

    # ========================================================
    # METRICS
    # ========================================================

    total_samples = len(results)

    detected_count = len(detected_samples)

    evaded_count = len(evaded_samples)

    detection_rate = (
        detected_count / total_samples
        if total_samples > 0
        else 0
    )

    evasion_rate = (
        evaded_count / total_samples
        if total_samples > 0
        else 0
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary = {
        "timestamp": datetime.now().isoformat(),

        "requested_valid_samples": int(num_samples),

        "total_ctgan_candidates_generated": int(
            total_generated
        ),

        "valid_samples_tested": int(
            total_samples
        ),

        "blue_team_threshold": float(
            BLUE_TEAM_THRESHOLD
        ),

        "detected_samples": int(
            detected_count
        ),

        "evaded_samples": int(
            evaded_count
        ),

        "detection_rate": float(
            detection_rate
        ),

        "evasion_rate": float(
            evasion_rate
        ),

        "fraud_probability": {
            "minimum": float(
                probabilities.min()
            ),

            "maximum": float(
                probabilities.max()
            ),

            "mean": float(
                probabilities.mean()
            ),

            "median": float(
                np.median(probabilities)
            )
        }
    }

    # ========================================================
    # PRINT RESULTS
    # ========================================================

    print("\n")
    print("=" * 70)
    print("FINAL ATTACK RESULTS")
    print("=" * 70)

    print(
        f"\nCTGAN candidates generated: "
        f"{total_generated}"
    )

    print(
        f"Valid samples tested:       "
        f"{total_samples}"
    )

    print(
        f"\nBlue Team threshold: "
        f"{BLUE_TEAM_THRESHOLD:.2f}"
    )

    print("\n--- BLUE TEAM OUTCOME ---")

    print(
        f"Detected: "
        f"{detected_count}"
    )

    print(
        f"Evaded:   "
        f"{evaded_count}"
    )

    print(
        f"\nDetection rate: "
        f"{detection_rate:.2%}"
    )

    print(
        f"Evasion rate:   "
        f"{evasion_rate:.2%}"
    )

    print("\n--- FRAUD PROBABILITY STATISTICS ---")

    print(
        f"Minimum: "
        f"{probabilities.min():.6f}"
    )

    print(
        f"Maximum: "
        f"{probabilities.max():.6f}"
    )

    print(
        f"Mean:    "
        f"{probabilities.mean():.6f}"
    )

    print(
        f"Median:  "
        f"{np.median(probabilities):.6f}"
    )

    # ========================================================
    # SAVE FILES
    # ========================================================

    results.to_csv(
        ALL_SAMPLES_PATH,
        index=False
    )

    evaded_samples.to_csv(
        EVADED_SAMPLES_PATH,
        index=False
    )

    detected_samples.to_csv(
        DETECTED_SAMPLES_PATH,
        index=False
    )

    with open(
        SUMMARY_PATH,
        "w"
    ) as f:

        json.dump(
            summary,
            f,
            indent=4
        )

    # ========================================================
    # OUTPUT PATHS
    # ========================================================

    print("\n")
    print("=" * 70)
    print("RESULTS SAVED")
    print("=" * 70)

    print(
        f"\nAll samples:\n{ALL_SAMPLES_PATH}"
    )

    print(
        f"\nEvaded samples:\n{EVADED_SAMPLES_PATH}"
    )

    print(
        f"\nDetected samples:\n{DETECTED_SAMPLES_PATH}"
    )

    print(
        f"\nSummary:\n{SUMMARY_PATH}"
    )

    print("\n")
    print("=" * 70)
    print("ADVERSARIAL ATTACK SIMULATION COMPLETE")
    print("=" * 70)

    return results, summary


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Change this number whenever you want.
    #
    # Examples:
    #
    # run_attack(num_samples=100)
    # run_attack(num_samples=500)
    # run_attack(num_samples=1000)
    # --------------------------------------------------------

    run_attack(
        num_samples=5000
    )
