import json
import numpy as np
import pandas as pd

from ctgan import CTGAN

from config import (
    CTGAN_MODEL_PATH,
    FEATURE_CONFIG_PATH,
    RANDOM_SEED,
)


class FraudGenerator:
    """
    Loads the trained CTGAN model and generates synthetic
    fraud-like merchant samples.
    """

    def __init__(self):
        self.model = None
        self.features = None
        self.discrete_columns = None

        self._load_feature_config()
        self._load_model()

    # ========================================================
    # LOAD FEATURE CONFIG
    # ========================================================

    def _load_feature_config(self):

        """Load the feature list CTGAN was trained on."""
        if not FEATURE_CONFIG_PATH.exists():
            raise FileNotFoundError(
                f"Feature config not found:\n{FEATURE_CONFIG_PATH}"
            )

        with open(FEATURE_CONFIG_PATH, "r") as f:
            config = json.load(f)

        self.features = config["FEATURES"]
        self.discrete_columns = config.get("DISCRETE_COLUMNS", [])

        print("\n[GENERATOR] Feature configuration loaded.")
        print(f"[GENERATOR] Number of features: {len(self.features)}")
        print(
            f"[GENERATOR] Discrete columns: "
            f"{self.discrete_columns}"
        )

    # ========================================================
    # LOAD CTGAN
    # ========================================================

    def _load_model(self):

        """Load the fitted CTGAN model."""
        if not CTGAN_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"CTGAN model not found:\n{CTGAN_MODEL_PATH}"
            )

        print("\n[GENERATOR] Loading trained CTGAN model...")

        try:
            self.model = CTGAN.load(str(CTGAN_MODEL_PATH))

        except Exception as e:
            raise RuntimeError(
                "\nFailed to load the CTGAN model.\n"
                "Make sure the 'ctgan' package version is compatible "
                "with the version used during training.\n\n"
                f"Original error:\n{e}"
            )

        print("[GENERATOR] CTGAN loaded successfully.")

    # ========================================================
    # GENERATE
    # ========================================================

    def generate(self, num_samples):

        """Sample synthetic fraud candidates from the learned minority distribution."""
        if num_samples <= 0:
            raise ValueError(
                "num_samples must be greater than 0."
            )

        np.random.seed(RANDOM_SEED)

        print(
            f"\n[GENERATOR] Generating "
            f"{num_samples} synthetic fraud candidates..."
        )

        try:
            samples = self.model.sample(num_samples)

        except Exception as e:
            raise RuntimeError(
                f"CTGAN generation failed:\n{e}"
            )

        samples = pd.DataFrame(samples)

        # ----------------------------------------------------
        # ENSURE EXPECTED FEATURE ORDER
        # ----------------------------------------------------

        missing_features = [
            col for col in self.features
            if col not in samples.columns
        ]

        if missing_features:
            raise ValueError(
                "Generated data is missing expected features:\n"
                f"{missing_features}"
            )

        samples = samples[self.features].copy()

        print(
            f"[GENERATOR] Generated shape: {samples.shape}"
        )

        return samples
