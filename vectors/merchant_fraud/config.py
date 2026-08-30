from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "outputs"


# ============================================================
# MODEL FILES
# ============================================================

CTGAN_MODEL_PATH = MODELS_DIR / "ctgan_fraud_model.pkl"

BLUE_TEAM_MODEL_PATH = MODELS_DIR / "final_blue_team_mlp.keras"

BLUE_TEAM_PREPROCESSOR_PATH = (
    MODELS_DIR / "final_blue_team_preprocessor.joblib"
)

FEATURE_CONFIG_PATH = MODELS_DIR / "feature_config.json"


# ============================================================
# OUTPUT FILES
# ============================================================

ALL_SAMPLES_PATH = RESULTS_DIR / "all_generated_samples.csv"

EVADED_SAMPLES_PATH = RESULTS_DIR / "evaded_samples.csv"

DETECTED_SAMPLES_PATH = RESULTS_DIR / "detected_samples.csv"

SUMMARY_PATH = RESULTS_DIR / "attack_summary.json"


# ============================================================
# ATTACK CONFIGURATION
# ============================================================

# Number of VALID synthetic samples we want for one simulation.
TARGET_VALID_SAMPLES = 100

# CTGAN samples generated in each attempt.
GENERATION_BATCH_SIZE = 200

# Prevents an infinite loop if generation repeatedly fails validation.
MAX_GENERATION_ROUNDS = 20


# ============================================================
# BLUE TEAM CONFIGURATION
# ============================================================

# Your final Blue Team evaluation used threshold = 0.5.
BLUE_TEAM_THRESHOLD = 0.50


# ============================================================
# RANDOM SEED
# ============================================================

RANDOM_SEED = 42