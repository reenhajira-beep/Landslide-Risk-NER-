import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score
)
from sklearn.model_selection import train_test_split


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "landslide_data.csv"
)

MODEL_PATH = (
    PROJECT_ROOT
    / "ml_artifacts"
    / "landslide_model.pkl"
)

METADATA_PATH = (
    PROJECT_ROOT
    / "ml_artifacts"
    / "model_metadata.json"
)


FEATURES = [
    "rainfall_mm_hr",
    "soil_moisture_pct",
    "tilt_deg",
    "vegetation_change_pct",
    "satellite_risk_index"
]

TARGET = "landslide_next_6h"


def train_model():

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    dataset = pd.read_csv(DATA_PATH)

    required_columns = FEATURES + [TARGET]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataset.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    if dataset.empty:
        raise ValueError(
            "Dataset is empty. Add real training rows."
        )

    if dataset[required_columns].isnull().any().any():
        raise ValueError(
            "Dataset contains missing values."
        )

    feature_data = dataset[FEATURES]
    target_data = dataset[TARGET].astype(int)

    if set(target_data.unique()) != {0, 1}:
        raise ValueError(
            "Target must contain both 0 and 1."
        )

    train_features, test_features, train_target, test_target = (
        train_test_split(
            feature_data,
            target_data,
            test_size=0.20,
            random_state=42,
            stratify=target_data
        )
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

    model.fit(
        train_features,
        train_target
    )

    predictions = model.predict(test_features)

    probabilities = model.predict_proba(
        test_features
    )[:, 1]

    metrics = {
        "accuracy": accuracy_score(
            test_target,
            predictions
        ),
        "precision": precision_score(
            test_target,
            predictions,
            zero_division=0
        ),
        "recall": recall_score(
            test_target,
            predictions,
            zero_division=0
        ),
        "f1_score": f1_score(
            test_target,
            predictions,
            zero_division=0
        ),
        "roc_auc": roc_auc_score(
            test_target,
            probabilities
        )
    }

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    joblib.dump(model, MODEL_PATH)

    metadata = {
        "model_type": "RandomForestClassifier",
        "features": FEATURES,
        "target": TARGET,
        "training_rows": len(dataset),
        "metrics": {
            name: round(float(value), 4)
            for name, value in metrics.items()
        }
    }

    METADATA_PATH.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8"
    )

    print("Model training completed")
    print(f"Model saved: {MODEL_PATH}")
    print(f"Metadata saved: {METADATA_PATH}")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    train_model()