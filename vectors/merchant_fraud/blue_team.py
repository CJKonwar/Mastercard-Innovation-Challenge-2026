import json
import numpy as np
import pandas as pd
import joblib

import tensorflow as tf

from config import (
    BLUE_TEAM_MODEL_PATH,
    BLUE_TEAM_PREPROCESSOR_PATH,
    FEATURE_CONFIG_PATH,
)


class BlueTeamDetector:
    """
    Final Blue Team fraud detector.

    Loads:
    1. Final Keras MLP
    2. Matching preprocessor
    3. Feature configuration
    """

    def __init__(self):

        self.model = None
        self.preprocessor = None
        self.features = None

        self._load_feature_config()
        self._load_preprocessor()
        self._load_model()

    # ========================================================
    # FEATURE CONFIG
    # ========================================================

    def _load_feature_config(self):

        """Load the feature list and categorical columns the model expects."""
        if not FEATURE_CONFIG_PATH.exists():
            raise FileNotFoundError(
                f"Feature config not found:\n"
                f"{FEATURE_CONFIG_PATH}"
            )

        with open(FEATURE_CONFIG_PATH, "r") as f:
            config = json.load(f)

        self.features = config["FEATURES"]

        print(
            "\n[BLUE TEAM] Feature configuration loaded."
        )
        print(
            f"[BLUE TEAM] Expected features: "
            f"{len(self.features)}"
        )

    # ========================================================
    # PREPROCESSOR
    # ========================================================

    def _load_preprocessor(self):

        """Load the fitted preprocessing pipeline."""
        if not BLUE_TEAM_PREPROCESSOR_PATH.exists():
            raise FileNotFoundError(
                f"Preprocessor not found:\n"
                f"{BLUE_TEAM_PREPROCESSOR_PATH}"
            )

        print(
            "\n[BLUE TEAM] Loading preprocessor..."
        )

        self.preprocessor = joblib.load(
            BLUE_TEAM_PREPROCESSOR_PATH
        )

        print(
            "[BLUE TEAM] Preprocessor loaded successfully."
        )

    # ========================================================
    # MODEL
    # ========================================================

    def _load_model(self):

        """Load the trained Keras classifier."""
        if not BLUE_TEAM_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Blue Team model not found:\n"
                f"{BLUE_TEAM_MODEL_PATH}"
            )

        print(
            "\n[BLUE TEAM] Loading final Blue Team MLP..."
        )

        self.model = tf.keras.models.load_model(
            BLUE_TEAM_MODEL_PATH,
            compile=False
        )

        print(
            "[BLUE TEAM] Final MLP loaded successfully."
        )

        print(
            f"[BLUE TEAM] Model input shape: "
            f"{self.model.input_shape}"
        )

    # ========================================================
    # PREPROCESS
    # ========================================================

    def preprocess(self, df):

        """Apply the same transforms used at training time, in the same column order."""
        missing = [
            col for col in self.features
            if col not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Input missing features:\n{missing}"
            )

        X = df[self.features].copy()

        X_processed = self.preprocessor.transform(X)

        X_processed = np.asarray(
            X_processed,
            dtype=np.float32
        )

        if np.isnan(X_processed).any():
            raise ValueError(
                "NaN found after preprocessing."
            )

        if np.isinf(X_processed).any():
            raise ValueError(
                "Infinite values found after preprocessing."
            )

        return X_processed

    # ========================================================
    # PREDICT
    # ========================================================

    def predict_proba(self, df):

        """Fraud probability per row."""
        X_processed = self.preprocess(df)

        probabilities = self.model.predict(
            X_processed,
            verbose=0
        )

        probabilities = np.asarray(
            probabilities
        ).reshape(-1)

        return probabilities

    # ========================================================
    # DETECT
    # ========================================================

    def detect(self, df, threshold=0.50):

        """Split candidates into detected and evaded at the given threshold."""
        probabilities = self.predict_proba(df)

        # Probability >= threshold means fraud is detected.
        detected = (
            probabilities >= threshold
        )

        return probabilities, detected
