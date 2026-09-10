import hashlib
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

import joblib
import pandas as pd


logger = logging.getLogger(__name__)


class LandslideModelService:

    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.model_version = None
        self.loaded_at = None
        self.last_error = None

        # Prevent simultaneous prediction operations
        # from interfering with one another.
        self.prediction_lock = Lock()

        self.model_path = (
            Path(__file__).resolve().parents[2]
            / "ml_artifacts"
            / "landslide_model.pkl"
        )

        # Feature order must be identical to training.
        self.feature_names = [
            "rainfall_mm_hr",
            "soil_moisture_pct",
            "tilt_deg",
            "vegetation_change_pct",
            "satellite_risk_index",
        ]

        # Expected input limits.
        self.feature_ranges = {
            "rainfall_mm_hr": (0.0, 500.0),
            "soil_moisture_pct": (0.0, 100.0),
            "tilt_deg": (0.0, 90.0),
            "vegetation_change_pct": (0.0, 100.0),
            "satellite_risk_index": (0.0, 1.0),
        }

    def calculate_model_version(self) -> str:
        """Create a short version ID from the model file."""

        file_hasher = hashlib.sha256()

        with self.model_path.open("rb") as model_file:
            while chunk := model_file.read(1024 * 1024):
                file_hasher.update(chunk)

        return file_hasher.hexdigest()[:12]

    def load_model(self) -> bool:
        """Load and validate the trained ML model."""

        self.model = None
        self.model_loaded = False
        self.model_version = None
        self.loaded_at = None
        self.last_error = None

        if not self.model_path.exists():
            self.last_error = (
                f"Model file was not found: {self.model_path}"
            )
            logger.error(self.last_error)
            return False

        try:
            loaded_model = joblib.load(self.model_path)

            if not hasattr(loaded_model, "predict_proba"):
                raise TypeError(
                    "The model does not support predict_proba()."
                )

            classes = getattr(loaded_model, "classes_", None)

            if classes is None or 1 not in list(classes):
                raise ValueError(
                    "The model does not contain positive class 1."
                )

            trained_feature_names = getattr(
                loaded_model,
                "feature_names_in_",
                None,
            )

            if trained_feature_names is not None:
                trained_feature_names = list(
                    trained_feature_names
                )

                if trained_feature_names != self.feature_names:
                    raise ValueError(
                        "Model feature names or order do not "
                        "match the backend configuration."
                    )

            expected_count = len(self.feature_names)
            actual_count = getattr(
                loaded_model,
                "n_features_in_",
                expected_count,
            )

            if actual_count != expected_count:
                raise ValueError(
                    f"Model expects {actual_count} features, "
                    f"but the backend provides {expected_count}."
                )

            self.model = loaded_model
            self.model_loaded = True
            self.model_version = (
                self.calculate_model_version()
            )
            self.loaded_at = datetime.now(
                timezone.utc
            ).isoformat()

            logger.info(
                "Landslide model loaded successfully: %s",
                type(self.model).__name__,
            )

            return True

        except Exception as error:
            self.last_error = (
                f"{type(error).__name__}: {error}"
            )
            logger.exception(
                "Unable to load the landslide model."
            )
            return False

    def prepare_features(
        self,
        rainfall_mm_hr: float,
        soil_moisture_pct: float,
        tilt_deg: float,
        vegetation_change_pct: float,
        satellite_risk_index: float,
    ) -> pd.DataFrame:
        """Validate inputs and build the model DataFrame."""

        values = {
            "rainfall_mm_hr": rainfall_mm_hr,
            "soil_moisture_pct": soil_moisture_pct,
            "tilt_deg": tilt_deg,
            "vegetation_change_pct": (
                vegetation_change_pct
            ),
            "satellite_risk_index": (
                satellite_risk_index
            ),
        }

        validated_values = {}

        for feature_name in self.feature_names:
            try:
                value = float(values[feature_name])
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"{feature_name} must be numeric."
                ) from error

            if not math.isfinite(value):
                raise ValueError(
                    f"{feature_name} must be a finite number."
                )

            minimum, maximum = self.feature_ranges[
                feature_name
            ]

            if value < minimum or value > maximum:
                raise ValueError(
                    f"{feature_name} must be between "
                    f"{minimum} and {maximum}."
                )

            validated_values[feature_name] = value

        return pd.DataFrame(
            [validated_values],
            columns=self.feature_names,
        )

    def predict_probability(
        self,
        rainfall_mm_hr: float,
        soil_moisture_pct: float,
        tilt_deg: float,
        vegetation_change_pct: float,
        satellite_risk_index: float,
    ) -> float:
        """Return the probability of landslide class 1."""

        if not self.model_loaded or self.model is None:
            raise RuntimeError(
                "landslide_model.pkl is not loaded."
            )

        input_data = self.prepare_features(
            rainfall_mm_hr=rainfall_mm_hr,
            soil_moisture_pct=soil_moisture_pct,
            tilt_deg=tilt_deg,
            vegetation_change_pct=(
                vegetation_change_pct
            ),
            satellite_risk_index=(
                satellite_risk_index
            ),
        )

        classes = list(self.model.classes_)
        positive_class_index = classes.index(1)

        with self.prediction_lock:
            probabilities = self.model.predict_proba(
                input_data
            )[0]

        probability = float(
            probabilities[positive_class_index]
        )

        # Extra safety against invalid model output.
        return max(0.0, min(1.0, probability))

    def get_feature_importance(self) -> dict[str, float]:
        """Return Random Forest feature importance."""

        if not self.model_loaded or self.model is None:
            return {}

        importance_values = getattr(
            self.model,
            "feature_importances_",
            None,
        )

        if importance_values is None:
            return {}

        importance = {
            feature_name: round(float(value), 4)
            for feature_name, value in zip(
                self.feature_names,
                importance_values,
            )
        }

        return dict(
            sorted(
                importance.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        )

    def get_status(self) -> dict:
        """Return safe information for model health."""

        modified_at = None

        if self.model_path.exists():
            modified_at = datetime.fromtimestamp(
                self.model_path.stat().st_mtime,
                timezone.utc,
            ).isoformat()

        return {
            "model_loaded": self.model_loaded,
            "model_path": str(self.model_path),
            "model_name": (
                type(self.model).__name__
                if self.model is not None
                else None
            ),
            "model_version": self.model_version,
            "required_features": self.feature_names,
            "feature_importance": (
                self.get_feature_importance()
            ),
            "model_modified_at": modified_at,
            "loaded_at": self.loaded_at,
            "last_error": self.last_error,
        }


model_service = LandslideModelService()