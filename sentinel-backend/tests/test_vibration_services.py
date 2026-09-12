"""Regression tests for SENTINEL-NER vibration and fusion services."""

import unittest

import numpy as np

from app.services.sensor_fusion_service import sensor_fusion_service
from app.services.vibration_service import vibration_service


class VibrationServiceTests(unittest.TestCase):
    SAMPLE_RATE = 100

    def signal(self, amplitude: float, seconds: int = 4):
        time = np.arange(self.SAMPLE_RATE * seconds) / self.SAMPLE_RATE
        return amplitude * np.sin(2 * np.pi * 8 * time)

    def test_extracts_true_dominant_frequency(self):
        features = vibration_service.extract_features(
            self.signal(0.04),
            self.signal(0.02),
            9.81 + self.signal(0.01),
            self.SAMPLE_RATE,
            0.10,
        )

        self.assertEqual(features["sample_count"], 400)
        self.assertAlmostEqual(
            features["dominant_frequency_hz"],
            8.0,
            places=1,
        )

    def test_rejects_unsynchronized_axes(self):
        with self.assertRaises(ValueError):
            vibration_service.extract_features(
                [0.0] * 32,
                [0.0] * 33,
                [9.81] * 32,
                self.SAMPLE_RATE,
            )

    def test_quiet_and_strong_windows_separate(self):
        quiet = vibration_service.extract_features(
            self.signal(0.005),
            self.signal(0.003),
            9.81 + self.signal(0.002),
            self.SAMPLE_RATE,
            0.05,
        )
        strong = vibration_service.extract_features(
            self.signal(0.30),
            self.signal(0.20),
            9.81 + self.signal(0.10),
            self.SAMPLE_RATE,
            1.20,
        )

        quiet_result = vibration_service.assess_movement(quiet)
        strong_result = vibration_service.assess_movement(strong)

        self.assertEqual(quiet_result["movement_status"], "NORMAL")
        self.assertEqual(strong_result["movement_status"], "ABNORMAL")
        self.assertGreater(
            strong_result["vibration_risk_score"],
            quiet_result["vibration_risk_score"],
        )


class SensorFusionTests(unittest.TestCase):
    def test_agreed_high_signals_generate_alert(self):
        result = sensor_fusion_service.fuse(
            environmental_result={
                "risk_score": 70,
                "risk_level": "HIGH",
                "contributing_factors": ["Heavy rainfall"],
                "recommended_actions": ["Operator review"],
                "model_used": "RandomForestClassifier",
            },
            vibration_result={
                "vibration_risk_score": 80,
                "vibration_risk_level": "CRITICAL",
                "abnormal_ground_movement": True,
                "contributing_factors": ["Elevated vibration"],
                "recommended_actions": ["Verify nearby sensors"],
            },
        )

        self.assertEqual(result["fused_risk_level"], "HIGH")
        self.assertTrue(result["alert_generated"])
        self.assertTrue(result["cross_sensor_corroboration"])

    def test_disagreement_requires_review_without_forced_alert(self):
        result = sensor_fusion_service.fuse(
            environmental_result={
                "risk_score": 20,
                "risk_level": "LOW",
                "contributing_factors": [],
                "recommended_actions": [],
                "model_used": "RandomForestClassifier",
            },
            vibration_result={
                "vibration_risk_score": 90,
                "vibration_risk_level": "CRITICAL",
                "abnormal_ground_movement": True,
                "contributing_factors": ["Elevated vibration"],
                "recommended_actions": ["Verify nearby sensors"],
            },
        )

        self.assertTrue(result["sensor_disagreement"])
        self.assertTrue(result["human_review_required"])
        self.assertFalse(result["alert_generated"])


if __name__ == "__main__":
    unittest.main()
