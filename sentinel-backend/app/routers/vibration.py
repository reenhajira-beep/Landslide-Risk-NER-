"""FastAPI routes for processing and storing ground-vibration windows."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.connection import get_database
from app.database.models import Alert, Prediction
from app.database.vibration_model import VibrationReading
from app.services.risk_agent import landslide_agent
from app.services.sensor_fusion_service import sensor_fusion_service
from app.services.vibration_service import vibration_service


router = APIRouter(
    prefix="/api/v1/vibration",
    tags=["Ground Vibration"],
)


class VibrationWindowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location_id: str = Field(min_length=1, max_length=100)
    sensor_id: str = Field(min_length=1, max_length=100)
    sample_rate_hz: float = Field(gt=0, le=5000)
    x_samples: list[float] = Field(min_length=32, max_length=20_000)
    y_samples: list[float] = Field(min_length=32, max_length=20_000)
    z_samples: list[float] = Field(min_length=32, max_length=20_000)
    tilt_change_deg: float = Field(default=0.0, ge=-90, le=90)
    captured_at: datetime | None = None

    @model_validator(mode="after")
    def validate_synchronized_axes(self):
        if not (
            len(self.x_samples)
            == len(self.y_samples)
            == len(self.z_samples)
        ):
            raise ValueError(
                "x_samples, y_samples and z_samples must have equal lengths."
            )

        return self


class VibrationReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: str
    sensor_id: str
    sample_rate_hz: float
    processing_status: str
    vibration_risk_score: float
    vibration_risk_level: str
    movement_status: str
    abnormal_ground_movement: bool
    contributing_factors: list[str]
    recommended_actions: list[str]
    assessment_mode: str
    sample_count: int
    window_duration_seconds: float
    vibration_amplitude: float
    rms_vibration: float
    peak_acceleration: float
    dominant_frequency_hz: float
    signal_energy: float
    tilt_change_deg: float
    x_rms: float
    y_rms: float
    z_rms: float
    captured_at: datetime
    created_at: datetime


class SensorFusionPredictionInput(VibrationWindowInput):
    """Environmental and vibration inputs for one fused prediction."""

    rainfall_mm_hr: float = Field(ge=0, le=500)
    soil_moisture_pct: float = Field(ge=0, le=100)
    tilt_deg: float = Field(ge=0, le=90)
    vegetation_change_pct: float = Field(ge=0, le=100)
    satellite_risk_index: float = Field(ge=0, le=1)


class SensorFusionPredictionResponse(BaseModel):
    prediction_id: int
    vibration_reading_id: int
    alert_id: int | None
    location_id: str
    environmental_risk_score: float
    environmental_risk_level: str
    vibration_risk_score: float
    vibration_risk_level: str
    fused_risk_score: float
    fused_risk_level: str
    alert_generated: bool
    human_review_required: bool
    sensor_disagreement: bool
    cross_sensor_corroboration: bool
    fusion_method: str
    model_used: str
    contributing_factors: list[str]
    recommended_actions: list[str]
    analysis_message: str
    vibration_analysis: VibrationReadingResponse


def _reading_response(
    reading: VibrationReading,
) -> dict:
    features = {
        "sample_count": reading.sample_count,
        "window_duration_seconds": reading.window_duration_seconds,
        "vibration_amplitude": reading.vibration_amplitude,
        "rms_vibration": reading.rms_vibration,
        "peak_acceleration": reading.peak_acceleration,
        "dominant_frequency_hz": reading.dominant_frequency_hz,
        "signal_energy": reading.signal_energy,
        "tilt_change_deg": reading.tilt_change_deg,
        "x_rms": reading.x_rms,
        "y_rms": reading.y_rms,
        "z_rms": reading.z_rms,
    }
    assessment = vibration_service.assess_movement(features)

    return {
        "id": reading.id,
        "location_id": reading.location_id,
        "sensor_id": reading.sensor_id,
        "sample_rate_hz": reading.sample_rate_hz,
        "processing_status": reading.processing_status,
        "captured_at": reading.captured_at,
        "created_at": reading.created_at,
        **features,
        **assessment,
    }


@router.post(
    "/analyze",
    response_model=VibrationReadingResponse,
    status_code=status.HTTP_201_CREATED,
)
def analyze_and_store_vibration(
    data: VibrationWindowInput,
    database: Session = Depends(get_database),
):
    """Extract features and save them together in PostgreSQL."""

    try:
        features = vibration_service.extract_features(
            x_samples=data.x_samples,
            y_samples=data.y_samples,
            z_samples=data.z_samples,
            sample_rate_hz=data.sample_rate_hz,
            tilt_change_deg=data.tilt_change_deg,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    captured_at = data.captured_at or datetime.now(timezone.utc)
    assessment = vibration_service.assess_movement(features)

    reading = VibrationReading(
        location_id=data.location_id.strip().upper(),
        sensor_id=data.sensor_id.strip().upper(),
        sample_rate_hz=data.sample_rate_hz,
        processing_status=(
            f"ANALYZED_{assessment['movement_status']}"
        ),
        captured_at=captured_at,
        **features,
    )

    try:
        database.add(reading)
        database.commit()
        database.refresh(reading)
    except SQLAlchemyError as error:
        database.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to save the vibration reading.",
        ) from error

    return _reading_response(reading)


@router.get(
    "/readings",
    response_model=list[VibrationReadingResponse],
)
def get_vibration_readings(
    location_id: str | None = None,
    sensor_id: str | None = None,
    limit: int = 100,
    database: Session = Depends(get_database),
):
    """Return the newest stored vibration feature windows."""

    safe_limit = max(1, min(limit, 500))
    query = select(VibrationReading)

    if location_id:
        query = query.where(
            VibrationReading.location_id == location_id.strip().upper()
        )

    if sensor_id:
        query = query.where(
            VibrationReading.sensor_id == sensor_id.strip().upper()
        )

    query = query.order_by(VibrationReading.id.desc()).limit(safe_limit)

    readings = database.scalars(query).all()

    return [
        _reading_response(reading)
        for reading in readings
    ]


@router.get("/thresholds")
def get_vibration_thresholds():
    """Expose the active prototype values for transparent calibration."""

    return {
        "acceleration_unit": "m/s^2",
        "rms_abnormal_mps2": vibration_service.rms_abnormal_mps2,
        "peak_abnormal_mps2": vibration_service.peak_abnormal_mps2,
        "tilt_abnormal_deg": vibration_service.tilt_abnormal_deg,
        "assessment_mode": "PROTOTYPE_CONFIGURABLE_THRESHOLDS",
        "operational_warning": (
            "Calibrate these values with local baseline and labelled "
            "field data before public-warning use."
        ),
    }


@router.post(
    "/fusion-predict",
    response_model=SensorFusionPredictionResponse,
    status_code=status.HTTP_201_CREATED,
)
def predict_with_sensor_fusion(
    data: SensorFusionPredictionInput,
    database: Session = Depends(get_database),
):
    """Fuse environmental ML with vibration evidence and save the result."""

    try:
        features = vibration_service.extract_features(
            x_samples=data.x_samples,
            y_samples=data.y_samples,
            z_samples=data.z_samples,
            sample_rate_hz=data.sample_rate_hz,
            tilt_change_deg=data.tilt_change_deg,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    vibration_result = vibration_service.assess_movement(features)
    environmental_result = landslide_agent.analyze(
        rainfall_mm_hr=data.rainfall_mm_hr,
        soil_moisture_pct=data.soil_moisture_pct,
        tilt_deg=data.tilt_deg,
        vegetation_change_pct=data.vegetation_change_pct,
        satellite_risk_index=data.satellite_risk_index,
    )
    fusion_result = sensor_fusion_service.fuse(
        environmental_result=environmental_result,
        vibration_result=vibration_result,
    )

    location_id = data.location_id.strip().upper()
    captured_at = data.captured_at or datetime.now(timezone.utc)

    reading = VibrationReading(
        location_id=location_id,
        sensor_id=data.sensor_id.strip().upper(),
        sample_rate_hz=data.sample_rate_hz,
        processing_status=(
            f"ANALYZED_{vibration_result['movement_status']}"
        ),
        captured_at=captured_at,
        **features,
    )

    prediction = Prediction(
        location_id=location_id,
        rainfall_mm_hr=data.rainfall_mm_hr,
        soil_moisture_pct=data.soil_moisture_pct,
        tilt_deg=data.tilt_deg,
        vegetation_change_pct=data.vegetation_change_pct,
        satellite_risk_index=data.satellite_risk_index,
        risk_score=fusion_result["fused_risk_score"],
        risk_level=fusion_result["fused_risk_level"],
        alert_generated=fusion_result["alert_generated"],
        model_used=fusion_result["model_used"],
    )

    alert = None

    try:
        database.add(reading)
        database.add(prediction)
        database.flush()

        if fusion_result["alert_generated"]:
            alert = Alert(
                prediction_id=prediction.id,
                location_id=location_id,
                risk_score=prediction.risk_score,
                risk_level=prediction.risk_level,
                message=(
                    f"{prediction.risk_level} sensor-fusion landslide "
                    f"risk detected at {location_id}. Operator "
                    "verification is required."
                ),
                status="ACTIVE",
            )
            database.add(alert)

        database.commit()
        database.refresh(reading)
        database.refresh(prediction)

        if alert is not None:
            database.refresh(alert)

    except SQLAlchemyError as error:
        database.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to save the sensor-fusion prediction.",
        ) from error

    return {
        "prediction_id": prediction.id,
        "vibration_reading_id": reading.id,
        "alert_id": alert.id if alert is not None else None,
        "location_id": location_id,
        **fusion_result,
        "vibration_analysis": _reading_response(reading),
    }
