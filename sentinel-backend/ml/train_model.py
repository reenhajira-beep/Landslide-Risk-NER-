import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    make_scorer,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    RandomizedSearchCV,
    StratifiedKFold,
    train_test_split,
)


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
    "satellite_risk_index",
]

TARGET = "landslide_next_6h"

FEATURE_RANGES = {
    "rainfall_mm_hr": (0, 500),
    "soil_moisture_pct": (0, 100),
    "tilt_deg": (0, 90),
    "vegetation_change_pct": (0, 100),
    "satellite_risk_index": (0, 1),
}

RANDOM_STATE = 42
TEST_SIZE = 0.20
PREDICTION_THRESHOLD = 0.50


def calculate_file_hash(file_path: Path) -> str:
    """Calculate a SHA-256 identifier for a file."""

    file_hasher = hashlib.sha256()

    with file_path.open("rb") as opened_file:
        while chunk := opened_file.read(1024 * 1024):
            file_hasher.update(chunk)

    return file_hasher.hexdigest()


def validate_dataset(
    dataset: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    """Validate and clean the training dataset."""

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
        raise ValueError("The dataset is empty.")

    dataset = dataset[required_columns].copy()

    if dataset.isnull().any().any():
        raise ValueError(
            "Dataset contains missing values."
        )

    for feature_name in FEATURES:
        dataset[feature_name] = pd.to_numeric(
            dataset[feature_name],
            errors="raise",
        )

    target_values = pd.to_numeric(
        dataset[TARGET],
        errors="raise",
    )

    if not target_values.isin([0, 1]).all():
        raise ValueError(
            "Target must contain only 0 and 1."
        )

    dataset[TARGET] = target_values.astype(int)

    if set(dataset[TARGET].unique()) != {0, 1}:
        raise ValueError(
            "Target must contain both classes 0 and 1."
        )

    feature_array = dataset[FEATURES].to_numpy(
        dtype=float
    )

    if not np.isfinite(feature_array).all():
        raise ValueError(
            "Dataset contains NaN or infinite values."
        )

    for feature_name, limits in FEATURE_RANGES.items():
        minimum, maximum = limits

        invalid_rows = ~dataset[feature_name].between(
            minimum,
            maximum,
        )

        if invalid_rows.any():
            raise ValueError(
                f"{feature_name} contains values outside "
                f"{minimum} to {maximum}."
            )

    duplicate_rows = int(
        dataset.duplicated(
            subset=required_columns
        ).sum()
    )

    # Remove duplicates to prevent the same row appearing
    # in both training and testing data.
    dataset = (
        dataset
        .drop_duplicates(subset=required_columns)
        .reset_index(drop=True)
    )

    class_counts = dataset[TARGET].value_counts()

    if int(class_counts.min()) < 5:
        raise ValueError(
            "Each target class needs at least five rows."
        )

    return dataset, duplicate_rows


def rounded(value: float) -> float:
    return round(float(value), 4)


def train_model() -> None:
    """Tune, evaluate and save the Random Forest."""

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    raw_dataset = pd.read_csv(DATA_PATH)
    raw_row_count = len(raw_dataset)

    dataset, duplicate_rows = validate_dataset(
        raw_dataset
    )

    feature_data = dataset[FEATURES]
    target_data = dataset[TARGET]

    (
        train_features,
        test_features,
        train_target,
        test_target,
    ) = train_test_split(
        feature_data,
        target_data,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=target_data,
    )

    minimum_training_class = int(
        train_target.value_counts().min()
    )

    cv_folds = min(5, minimum_training_class)

    cross_validation = StratifiedKFold(
        n_splits=cv_folds,
        shuffle=True,
        random_state=RANDOM_STATE,
    )

    base_model = RandomForestClassifier(
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    parameter_options = {
        "n_estimators": [200, 300, 400, 500],
        "max_depth": [None, 8, 12, 16, 20],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4],
        "max_features": ["sqrt", "log2", None],
        "class_weight": [
            "balanced",
            "balanced_subsample",
        ],
    }

    scoring = {
        "roc_auc": "roc_auc",
        "balanced_accuracy": "balanced_accuracy",
        "precision": make_scorer(
            precision_score,
            zero_division=0,
        ),
        "recall": make_scorer(
            recall_score,
            zero_division=0,
        ),
        "f1": make_scorer(
            f1_score,
            zero_division=0,
        ),
    }

    search = RandomizedSearchCV(
        estimator=base_model,
        param_distributions=parameter_options,
        n_iter=12,
        scoring=scoring,
        refit="roc_auc",
        cv=cross_validation,
        random_state=RANDOM_STATE,
        n_jobs=1,
        verbose=1,
        return_train_score=True,
        error_score="raise",
    )

    print("Starting Random Forest tuning...")
    search.fit(train_features, train_target)

    best_model = search.best_estimator_

    probabilities = best_model.predict_proba(
        test_features
    )[:, 1]

    predictions = (
        probabilities >= PREDICTION_THRESHOLD
    ).astype(int)

    true_negative, false_positive, false_negative, true_positive = (
        confusion_matrix(
            test_target,
            predictions,
            labels=[0, 1],
        ).ravel()
    )

    specificity = (
        true_negative
        / (true_negative + false_positive)
        if true_negative + false_positive
        else 0
    )

    holdout_metrics = {
        "accuracy": rounded(
            accuracy_score(test_target, predictions)
        ),
        "balanced_accuracy": rounded(
            balanced_accuracy_score(
                test_target,
                predictions,
            )
        ),
        "precision": rounded(
            precision_score(
                test_target,
                predictions,
                zero_division=0,
            )
        ),
        "recall": rounded(
            recall_score(
                test_target,
                predictions,
                zero_division=0,
            )
        ),
        "specificity": rounded(specificity),
        "f1_score": rounded(
            f1_score(
                test_target,
                predictions,
                zero_division=0,
            )
        ),
        "roc_auc": rounded(
            roc_auc_score(
                test_target,
                probabilities,
            )
        ),
        "average_precision": rounded(
            average_precision_score(
                test_target,
                probabilities,
            )
        ),
        "brier_score": rounded(
            brier_score_loss(
                test_target,
                probabilities,
            )
        ),
    }

    best_index = search.best_index_

    cross_validation_metrics = {
        "folds": cv_folds,
        "mean_roc_auc": rounded(
            search.cv_results_[
                "mean_test_roc_auc"
            ][best_index]
        ),
        "std_roc_auc": rounded(
            search.cv_results_[
                "std_test_roc_auc"
            ][best_index]
        ),
        "mean_balanced_accuracy": rounded(
            search.cv_results_[
                "mean_test_balanced_accuracy"
            ][best_index]
        ),
        "mean_precision": rounded(
            search.cv_results_[
                "mean_test_precision"
            ][best_index]
        ),
        "mean_recall": rounded(
            search.cv_results_[
                "mean_test_recall"
            ][best_index]
        ),
        "mean_f1_score": rounded(
            search.cv_results_[
                "mean_test_f1"
            ][best_index]
        ),
        "mean_training_roc_auc": rounded(
            search.cv_results_[
                "mean_train_roc_auc"
            ][best_index]
        ),
    }

    feature_importance = {
        feature_name: rounded(importance)
        for feature_name, importance in sorted(
            zip(
                FEATURES,
                best_model.feature_importances_,
            ),
            key=lambda item: item[1],
            reverse=True,
        )
    }

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(best_model, MODEL_PATH)

    model_hash = calculate_file_hash(MODEL_PATH)
    dataset_hash = calculate_file_hash(DATA_PATH)

    class_distribution = {
        str(class_name): int(count)
        for class_name, count
        in target_data.value_counts().sort_index().items()
    }

    metadata = {
        "model_type": type(best_model).__name__,
        "model_version": model_hash[:12],
        "trained_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "features": FEATURES,
        "target": TARGET,
        "training_rows": len(dataset),
        "dataset": {
            "path": str(DATA_PATH),
            "sha256": dataset_hash,
            "raw_rows": raw_row_count,
            "usable_rows": len(dataset),
            "duplicates_removed": duplicate_rows,
            "class_distribution": class_distribution,
        },
        "split": {
            "training_rows": len(train_features),
            "testing_rows": len(test_features),
            "test_size": TEST_SIZE,
            "random_state": RANDOM_STATE,
        },
        "best_parameters": search.best_params_,
        "decision_threshold": PREDICTION_THRESHOLD,
        "cross_validation": cross_validation_metrics,
        "metrics": holdout_metrics,
        "confusion_matrix": {
            "true_negative": int(true_negative),
            "false_positive": int(false_positive),
            "false_negative": int(false_negative),
            "true_positive": int(true_positive),
        },
        "feature_importance": feature_importance,
        "production_ready": False,
        "warning": (
            "Prototype model. Validate using independent "
            "real NER landslide observations before "
            "operational emergency use."
        ),
    }

    METADATA_PATH.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("\nModel training completed")
    print(f"Model saved: {MODEL_PATH}")
    print(f"Metadata saved: {METADATA_PATH}")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    train_model()