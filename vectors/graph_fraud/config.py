"""
Configuration for the Adversarial Closed-Loop System.
Centralizes all hyperparameters, model settings, and paths.
"""
from typing import Tuple

# =====================================================================
# PATHS
# =====================================================================
CTGAN_MODEL_PATH: str = "models/ctgan_legit_model.pkl"
SEED_ACCOUNTS_PATH: str = "data/seed_accounts_nodes.csv"
MODEL_SAVE_PATH: str = "models/hardened_blue_team_model.pt"
METRICS_SAVE_PATH: str = "outputs/adversarial_loop_metrics.json"

# =====================================================================
# ADVERSARIAL LOOP SETTINGS
# =====================================================================
NUM_EPOCHS: int = 12
N_LEGIT_PER_EPOCH: int = 3000
USE_HGT: bool = True  # Toggle for Heterogeneous Graph Transformer

# =====================================================================
# RED TEAM / GEMINI LLM SETTINGS
# =====================================================================
import os
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
GEMINI_MODEL_NAME: str = "gemini-2.5-pro"

# =====================================================================
# BLUE TEAM (HGT) HYPERPARAMETERS
# =====================================================================
HIDDEN_CHANNELS: int = 64
NUM_HEADS: int = 4
NUM_LAYERS: int = 2
LR: float = 0.01
WEIGHT_DECAY: float = 5e-4
FOCAL_GAMMA: float = 2.0
NODE_WEIGHT_CAP: float = 5.0
EDGE_WEIGHT_CAP: float = 10.0
EARLY_STOP_PATIENCE: int = 60

# =====================================================================
# FEATURE CONSTANTS
# =====================================================================
NODE_FEATURE_NAMES: Tuple[str, ...] = (
    'account_age_days', 'in_degree', 'out_degree', 'pagerank',
    'wcc_size', 'device_shared_count', 'ip_shared_count'
)

EDGE_FEATURE_NAMES: Tuple[str, ...] = (
    'amount', 'dwell_time_seconds', 'is_structured'
)
