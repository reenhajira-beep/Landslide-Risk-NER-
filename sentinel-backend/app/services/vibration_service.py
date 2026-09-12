"""Ground-vibration signal processing for SENTINEL-NER.

The service accepts synchronized X/Y/Z acceleration samples, removes the
stationary component and light high-frequency noise, and calculates features
that can later be supplied to the landslide sensor-fusion model.
"""

from __future__ import annotations

import os
from typing import Sequence

import numpy as np


class VibrationService:
    """Validate sensor windows and extract vibration features."""

    MINIMUM_SAMPLES = 32
    MAXIMUM_SAMPLES = 20_000

    def __init__(self) -> None:
        # Prototype defaults in m/s^2 and degrees. Every threshold can be
        # calibrated per deployment without changing source code.
        self.rms_abnormal_mps2 = self._read_positive_setting(
            "VIBRATION_RMS_ABNORMAL_MPS2",
            0.08,
        )
        self.peak_abnormal_mps2 = self._read_positive_setting(
            "VIBRATION_PEAK_ABNORMAL_MPS2",
            0.25,
        )
        self.tilt_abnormal_deg = self._read_positive_setting(
            "VIBRATION_TILT_ABNORMAL_DEG",
            0.75,
        )

    @staticmethod
    def _read_positive_setting(name: str, default: float) -> float:
        raw_value = os.getenv(name)

        if raw_value is None:
            return default

        try:
            value = float(raw_value)
        except ValueError:
            return default

        return value if value > 0 else default

    @staticmethod
    def _as_finite_array(
        values: Sequence[float],
        axis_name: str,
    ) -> np.ndarray:
        array = np.asarray(values, dtype=float)

        if array.ndim != 1:
            raise ValueError(
                f"{axis_name} samples must be a one-dimensional list."
            )

        if not np.isfinite(array).all():
            raise ValueError(
                f"{axis_name} samples contain NaN or infinite values."
            )

        return array

    def _validate_window(
        self,
        x_samples: np.ndarray,
        y_samples: np.ndarray,
        z_samples: np.ndarray,
        sample_rate_hz: float,
        tilt_change_deg: float,
    ) -> None:
        sample_count = len(x_samples)

        if len(y_samples) != sample_count or len(z_samples) != sample_count:
            raise ValueError(
                "X, Y and Z must contain the same number of samples."
            )

        if not self.MINIMUM_SAMPLES <= sample_count <= self.MAXIMUM_SAMPLES:
            raise ValueError(
                "Each vibration window must contain between "
                f"{self.MINIMUM_SAMPLES} and {self.MAXIMUM_SAMPLES} samples."
            )

        if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be greater than zero.")

        if sample_rate_hz > 5_000:
            raise ValueError("sample_rate_hz cannot exceed 5000 Hz.")

        if not np.isfinite(tilt_change_deg):
            raise ValueError("tilt_change_deg must be a finite number.")

    @staticmethod
    def _moving_average(
        signal: np.ndarray,
        window_size: int,
    ) -> np.ndarray:
        if window_size <= 1:
            return signal.copy()

        kernel = np.ones(window_size, dtype=float) / window_size

        return np.apply_along_axis(
            lambda axis: np.convolve(axis, kernel, mode="same"),
            axis=0,
            arr=signal,
        )

    @staticmethod
    def _dominant_frequency(
        filtered_window: np.ndarray,
        sample_rate_hz: float,
    ) -> float:
        # Combine the spectral power of all three signed axes. Calculating an
        # FFT from vector magnitude can double the apparent frequency because
        # magnitude removes the signal's negative half-cycle.
        spectrum = np.fft.rfft(filtered_window, axis=0)
        combined_power = np.sum(np.square(np.abs(spectrum)), axis=1)
        frequencies = np.fft.rfftfreq(
            len(filtered_window),
            d=1.0 / sample_rate_hz,
        )

        # Ignore the zero-frequency/DC component.
        if len(combined_power) <= 1:
            return 0.0

        combined_power[0] = 0.0
        strongest_index = int(np.argmax(combined_power))

        return float(frequencies[strongest_index])

    def extract_features(
        self,
        x_samples: Sequence[float],
        y_samples: Sequence[float],
        z_samples: Sequence[float],
        sample_rate_hz: float,
        tilt_change_deg: float = 0.0,
    ) -> dict[str, float | int]:
        """Return model-ready features from one synchronized sensor window.

        Acceleration samples must use one consistent unit, preferably m/s^2.
        The filter used here is suitable for a prototype. Field deployment
        requires sensor calibration and a site-specific band-pass filter.
        """

        x_axis = self._as_finite_array(x_samples, "X")
        y_axis = self._as_finite_array(y_samples, "Y")
        z_axis = self._as_finite_array(z_samples, "Z")

        self._validate_window(
            x_axis,
            y_axis,
            z_axis,
            float(sample_rate_hz),
            float(tilt_change_deg),
        )

        sensor_window = np.column_stack((x_axis, y_axis, z_axis))

        # Remove the stationary component, including accelerometer gravity.
        dynamic_window = sensor_window - np.mean(
            sensor_window,
            axis=0,
            keepdims=True,
        )

        # Smooth approximately 30 ms of data without destroying the event.
        smoothing_size = max(1, int(round(sample_rate_hz * 0.03)))
        smoothing_size = min(smoothing_size, 9)

        if smoothing_size % 2 == 0:
            smoothing_size += 1

        filtered_window = self._moving_average(
            dynamic_window,
            smoothing_size,
        )

        magnitude = np.linalg.norm(filtered_window, axis=1)
        axis_rms = np.sqrt(np.mean(np.square(filtered_window), axis=0))

        rms_vibration = float(
            np.sqrt(np.mean(np.square(magnitude)))
        )
        peak_acceleration = float(np.max(magnitude))
        vibration_amplitude = float(np.ptp(magnitude))
        signal_energy = float(np.mean(np.square(magnitude)))
        dominant_frequency_hz = self._dominant_frequency(
            filtered_window,
            float(sample_rate_hz),
        )

        return {
            "sample_count": int(len(magnitude)),
            "window_duration_seconds": round(
                len(magnitude) / float(sample_rate_hz),
                4,
            ),
            "vibration_amplitude": round(vibration_amplitude, 6),
            "rms_vibration": round(rms_vibration, 6),
            "peak_acceleration": round(peak_acceleration, 6),
            "dominant_frequency_hz": round(
                dominant_frequency_hz,
                4,
            ),
            "signal_energy": round(signal_energy, 8),
            "tilt_change_deg": round(abs(float(tilt_change_deg)), 4),
            "x_rms": round(float(axis_rms[0]), 6),
            "y_rms": round(float(axis_rms[1]), 6),
            "z_rms": round(float(axis_rms[2]), 6),
        }

    @staticmethod
    def _risk_level(score: float) -> str:
        if score <= 25:
            return "LOW"

        if score <= 50:
            return "MODERATE"

        if score <= 75:
            return "HIGH"

        return "CRITICAL"

    def assess_movement(
        self,
        features: dict[str, float | int],
    ) -> dict[str, object]:
        """Create a transparent prototype abnormal-movement assessment.

        This score is intentionally separate from the trained landslide ML
        probability. Its thresholds must be calibrated with local baseline
        and labelled field data before operational public-warning use.
        """

        rms_vibration = float(features["rms_vibration"])
        peak_acceleration = float(features["peak_acceleration"])
        tilt_change = abs(float(features["tilt_change_deg"]))

        rms_component = min(
            rms_vibration / self.rms_abnormal_mps2,
            1.0,
        )
        peak_component = min(
            peak_acceleration / self.peak_abnormal_mps2,
            1.0,
        )
        tilt_component = min(
            tilt_change / self.tilt_abnormal_deg,
            1.0,
        )

        score = round(
            100
            * (
                0.45 * rms_component
                + 0.35 * peak_component
                + 0.20 * tilt_component
            ),
            2,
        )
        risk_level = self._risk_level(score)

        if risk_level == "LOW":
            movement_status = "NORMAL"
            recommended_actions = [
                "Continue normal sensor monitoring",
            ]
        elif risk_level == "MODERATE":
            movement_status = "WATCH"
            recommended_actions = [
                "Increase vibration sampling frequency",
                "Check the sensor mounting and local baseline",
            ]
        elif risk_level == "HIGH":
            movement_status = "ABNORMAL"
            recommended_actions = [
                "Request an immediate operator review",
                "Compare rainfall, moisture and slope indicators",
                "Inspect the monitored slope if conditions are safe",
            ]
        else:
            movement_status = "ABNORMAL"
            recommended_actions = [
                "Escalate to the disaster-management operator",
                "Verify the event using nearby sensors",
                "Follow the approved local emergency protocol",
            ]

        contributing_factors: list[str] = []

        if rms_component >= 0.5:
            contributing_factors.append(
                "Elevated continuous ground vibration"
            )

        if peak_component >= 0.5:
            contributing_factors.append(
                "Elevated peak ground acceleration"
            )

        if tilt_component >= 0.5:
            contributing_factors.append(
                "Significant tilt change"
            )

        if not contributing_factors:
            contributing_factors.append(
                "No major vibration anomaly detected"
            )

        return {
            "vibration_risk_score": score,
            "vibration_risk_level": risk_level,
            "movement_status": movement_status,
            "abnormal_ground_movement": risk_level
            in {"HIGH", "CRITICAL"},
            "contributing_factors": contributing_factors,
            "recommended_actions": recommended_actions,
            "assessment_mode": "PROTOTYPE_CONFIGURABLE_THRESHOLDS",
        }


vibration_service = VibrationService()
