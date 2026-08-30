"""
save_model.py — trains Layer 2 once and writes the fitted model to disk as
an actual artifact, rather than the in-memory-only model that
train_layer2.py / evaluate_pipeline.py produce and discard on exit.

Writes two files to outputs/:

  layer2_model.txt   native LightGBM Booster format. Human-readable-ish,
                      no dependency on scikit-learn or a matching library
                      version to reload -- the safer format to hand to
                      someone outside this repo.

  layer2_model.pkl    joblib-pickled sklearn-API LGBMClassifier -- the same
                      object type train_and_evaluate() returns in memory,
                      so it drops straight back into code that expects
                      model.predict_proba(...) etc.

Run: python save_model.py
"""

import os

import joblib

from train_layer2 import train_and_evaluate

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")


def main():
    model, df, _ = train_and_evaluate()

    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    booster_path = os.path.join(ARTIFACT_DIR, "layer2_model.txt")
    model.booster_.save_model(booster_path)
    print(f"\nSaved native LightGBM booster to {booster_path}")

    pkl_path = os.path.join(ARTIFACT_DIR, "layer2_model.pkl")
    joblib.dump(model, pkl_path)
    print(f"Saved joblib-pickled sklearn model to {pkl_path}")

    print(
        "\nTo reload:\n"
        "  import joblib\n"
        "  model = joblib.load('outputs/layer2_model.pkl')\n"
        "  model.predict_proba(X)  # X must have the same MODEL_FEATURES columns as features.py\n"
    )


if __name__ == "__main__":
    main()
