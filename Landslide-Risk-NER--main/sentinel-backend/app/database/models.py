from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.database.connection import Base
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


# Stores every landslide-risk prediction.
class Prediction(Base):
    __tablename__ = "predictions"

    # Automatically generated prediction ID.
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # Location being monitored.
    location_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # Environmental input values.
    rainfall_mm_hr: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    soil_moisture_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    tilt_deg: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    vegetation_change_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    satellite_risk_index: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # ML model prediction results.
    risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    alert_generated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    model_used: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # PostgreSQL automatically stores the prediction time.
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


# Stores alerts generated for HIGH or CRITICAL predictions.
class Alert(Base):
    __tablename__ = "alerts"

    # Automatically generated alert ID.
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # Connects the alert to its prediction.
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey(
            "predictions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    # Location where the alert was generated.
    location_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # Risk information copied from the prediction.
    risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Warning message for dashboard/SMS/mobile services.
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Possible values: ACTIVE or ACKNOWLEDGED.
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
        index=True,
    )

    # Time when the alert was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Filled when an operator acknowledges the alert.
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


# Stores hazard reports submitted by community members.
class CommunityReport(Base):
    __tablename__ = "community_reports"

    # Automatically generated community report ID.
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # Location connected to the report.
    location_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # Examples:
    # SOIL_CRACK, ROCKFALL, WATER_SEEPAGE,
    # GROUND_MOVEMENT or OTHER.
    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Information provided by the community member.
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # LOW, MODERATE, HIGH or CRITICAL.
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="MODERATE",
        server_default="MODERATE",
    )

    # Optional GIS latitude coordinate.
    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Optional GIS longitude coordinate.
    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Optional name of the person submitting the report.
    reporter_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # PENDING, VERIFIED, RESOLVED or REJECTED.
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        index=True,
    )

    # PostgreSQL automatically stores the submission time.
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Filled when an administrator reviews the report.
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
class LiveMonitoring(Base):
    __tablename__ = "live_monitoring"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    location_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    location_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    temperature_c: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    rainfall_mm_hr: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    relative_humidity_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    wind_speed_kmh: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    soil_moisture_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    tilt_deg: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    vegetation_change_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    satellite_risk_index: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    risk_level: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    alert_generated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    weather_time: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )