"""Database model for NASA GPM IMERG point rainfall observations."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class SatelliteRainfall(Base):
    """One IMERG grid-cell observation for a monitored location."""

    __tablename__ = "satellite_rainfall"

    __table_args__ = (
        UniqueConstraint(
            "location_id",
            "source_file",
            name="uq_satellite_rainfall_location_source",
        ),
        Index(
            "ix_satellite_rainfall_location_period",
            "location_id",
            "period_end",
        ),
    )

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

    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="NASA_GPM_PPS",
        server_default="NASA_GPM_PPS",
    )

    product: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="IMERG_EARLY_GIS_30MIN",
        server_default="IMERG_EARLY_GIS_30MIN",
    )

    product_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    source_file: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    accumulation_mm: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    rainfall_rate_mm_hr: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    raw_pixel_value: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    grid_row: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    grid_column: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    resolution_degrees: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.1,
        server_default="0.1",
    )

    data_latency_minutes: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    quality_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )

    is_missing: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
