from pathlib import Path

import joblib
import pandas as pd


class LandslideModelService:

    def __init__(self):
        self.model = None
        self.model_loaded = False

        self.model_path = (
            Path(__file__).resolve().parents[2]
            / "ml_artifacts"
            / "landslide_model.pkl"
        )

        self.feature_names = [
            "rainfall_mm_hr",
            "soil_moisture_pct",
            "tilt_deg",
            "vegetation_change_pct",
            "satellite_risk_index"
        ]

    def load_model(self) -> bool:
        """
        Load the trusted trained model.
        Return False if the model file does not exist.
        """

        if not self.model_path.exists():
            self.model = None
            self.model_loaded = False
            return False

        self.model = joblib.load(
            self.model_path
        )

        self.model_loaded = True
        return True

    def predict_probability(
        self,
        rainfall_mm_hr: float,
        soil_moisture_pct: float,
        tilt_deg: float,
        vegetation_change_pct: float,
        satellite_risk_index: float
    ) -> float:

        if not self.model_loaded:
            raise RuntimeError(
                "landslide_model.pkl is not loaded"
            )

        input_data = pd.DataFrame(
            [[
                rainfall_mm_hr,
                soil_moisture_pct,
                tilt_deg,
                vegetation_change_pct,
                satellite_risk_index
            ]],
            columns=self.feature_names
        )

        probability = self.model.predict_proba(
            input_data
        )[0][1]

        return float(probability)

    def get_status(self) -> dict:
        return {
            "model_loaded": self.model_loaded,
            "model_path": str(self.model_path),
            "model_name": (
                type(self.model).__name__
                if self.model is not None
                else None
            ),
            "required_features": self.feature_names
        }


model_service = LandslideModelService()