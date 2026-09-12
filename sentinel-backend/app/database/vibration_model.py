"""Database model for extracted ground-vibration features."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class VibrationReading(Base):
    """Stores one processed accelerometer/geophone sampling window."""

    __tablename__ = "vibration_readings"

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

    sensor_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    sample_rate_hz: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    sample_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    window_duration_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    vibration_amplitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    rms_vibration: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        index=True,
    )

    peak_acceleration: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    dominant_frequency_hz: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    signal_energy: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    tilt_change_deg: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    x_rms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    y_rms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    z_rms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    processing_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="FEATURES_EXTRACTED",
        server_default="FEATURES_EXTRACTED",
    )

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
