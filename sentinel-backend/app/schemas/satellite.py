"""Schemas returned by the satellite rainfall data server."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SatelliteRainfallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: str
    location_name: str
    state: str
    latitude: float
    longitude: float
    provider: str
    product: str
    product_version: str
    source_file: str
    period_start: datetime
    period_end: datetime
    accumulation_mm: float | None
    rainfall_rate_mm_hr: float | None
    raw_pixel_value: int
    grid_row: int
    grid_column: int
    resolution_degrees: float
    data_latency_minutes: float
    quality_status: str
    is_missing: bool
    fetched_at: datetime


class SatelliteRefreshResponse(BaseModel):
    status: str
    created: bool
    measurement: SatelliteRainfallResponse


class SatelliteRefreshAllResponse(BaseModel):
    status: str
    source_file: str
    period_end: datetime
    location_count: int
    created_count: int
    existing_count: int
    missing_count: int
    measurements: list[SatelliteRainfallResponse]


class SatelliteModelInputResponse(BaseModel):
    location_id: str
    rainfall_mm_hr: float | None
    usable_for_prediction: bool
    freshness_status: str
    maximum_age_hours: float
    quality_status: str
    provider: str
    product: str
    product_version: str
    source_file: str
    observed_at: datetime
    data_age_hours: float
    warning: str
