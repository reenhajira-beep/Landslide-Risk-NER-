"""Explainable prototype fusion of environmental ML and vibration risk."""

import os


class SensorFusionService:
    """Combine two independent risk signals without hiding either result."""

    def __init__(self) -> None:
        self.environment_weight = self._environment_weight()
        self.vibration_weight = round(1.0 - self.environment_weight, 4)

    @staticmethod
    def _environment_weight() -> float:
        try:
            configured = float(
                os.getenv("SENSOR_FUSION_ENVIRONMENT_WEIGHT", "0.75")
            )
        except ValueError:
            configured = 0.75

        # Environmental ML remains the primary signal until the vibration
        # feature has enough labelled field data for retraining.
        return min(max(configured, 0.50), 0.90)

    @staticmethod
    def _risk_level(score: float) -> str:
        if score <= 25:
            return "LOW"

        if score <= 50:
            return "MODERATE"

        if score <= 75:
            return "HIGH"

        return "CRITICAL"

    @staticmethod
    def _unique(items: list[str]) -> list[str]:
        return list(dict.fromkeys(items))

    def fuse(
        self,
        environmental_result: dict,
        vibration_result: dict,
    ) -> dict[str, object]:
        environmental_score = min(
            max(float(environmental_result["risk_score"]), 0.0),
            100.0,
        )
        vibration_score = min(
            max(float(vibration_result["vibration_risk_score"]), 0.0),
            100.0,
        )

        fused_score = round(
            environmental_score * self.environment_weight
            + vibration_score * self.vibration_weight,
            2,
        )
        fused_level = self._risk_level(fused_score)
        alert_generated = fused_level in {"HIGH", "CRITICAL"}

        score_difference = abs(environmental_score - vibration_score)
        sensor_disagreement = score_difference >= 40
        cross_sensor_corroboration = (
            environmental_score > 50 and vibration_score > 50
        )
        human_review_required = (
            alert_generated
            or sensor_disagreement
            or bool(vibration_result["abnormal_ground_movement"])
        )

        factors = list(
            environmental_result.get("contributing_factors", [])
        )
        factors.extend(
            f"Vibration: {factor}"
            for factor in vibration_result.get("contributing_factors", [])
        )

        if cross_sensor_corroboration:
            factors.append(
                "Environmental and vibration sensors both indicate risk"
            )

        if sensor_disagreement:
            factors.append(
                "Environmental and vibration scores differ significantly"
            )

        actions = list(
            environmental_result.get("recommended_actions", [])
        )
        actions.extend(
            vibration_result.get("recommended_actions", [])
        )

        if human_review_required:
            actions.append(
                "Require operator verification before a public warning"
            )

        environmental_model = environmental_result.get(
            "model_used",
            "environmental_model",
        )
        fusion_method = (
            f"prototype_weighted_fusion_v1:{self.environment_weight:.2f}/"
            f"{self.vibration_weight:.2f}"
        )

        return {
            "environmental_risk_score": round(environmental_score, 2),
            "environmental_risk_level": environmental_result["risk_level"],
            "vibration_risk_score": round(vibration_score, 2),
            "vibration_risk_level": vibration_result[
                "vibration_risk_level"
            ],
            "fused_risk_score": fused_score,
            "fused_risk_level": fused_level,
            "alert_generated": alert_generated,
            "human_review_required": human_review_required,
            "sensor_disagreement": sensor_disagreement,
            "cross_sensor_corroboration": cross_sensor_corroboration,
            "contributing_factors": self._unique(factors),
            "recommended_actions": self._unique(actions),
            "fusion_method": fusion_method,
            "model_used": f"{environmental_model}+{fusion_method}",
            "analysis_message": (
                "Environmental ML and ground-vibration evidence produced "
                f"a {fused_level.lower()} fused landslide-risk assessment."
            ),
        }


sensor_fusion_service = SensorFusionService()
