"""FastAPI routes for the NASA GPM IMERG satellite rainfall server."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.data.monitoring_locations import LIVE_LOCATIONS
from app.database.connection import get_database
from app.database.satellite_model import SatelliteRainfall
from app.schemas.satellite import (
    SatelliteModelInputResponse,
    SatelliteRainfallResponse,
    SatelliteRefreshAllResponse,
    SatelliteRefreshResponse,
)
from app.services.imerg_service import (
    IMERGAuthenticationError,
    IMERGNotConfiguredError,
    IMERGProductError,
    IMERGProviderError,
    imerg_service,
)
from app.services.satellite_collector import satellite_collector


router = APIRouter(
    prefix="/api/v1/satellite",
    tags=["NASA Satellite Rainfall"],
)


def _require_refresh_key(
    supplied_key: Annotated[
        str | None,
        Header(alias="X-Satellite-Refresh-Key"),
    ] = None,
) -> None:
    """Protect expensive provider refreshes when a key is configured."""

    expected_key = os.getenv(
        "SATELLITE_REFRESH_API_KEY",
        "",
    ).strip()

    if not expected_key:
        return

    if not supplied_key or not secrets.compare_digest(
        supplied_key,
        expected_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "A valid X-Satellite-Refresh-Key header is required."
            ),
        )


def _raise_provider_http_error(error: Exception) -> None:
    if isinstance(error, IMERGNotConfiguredError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    if isinstance(error, IMERGAuthenticationError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    if isinstance(error, (IMERGProviderError, IMERGProductError)):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    if isinstance(error, SQLAlchemyError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to store NASA IMERG rainfall data.",
        ) from error

    raise error


def _latest_measurement(
    database: Session,
    location_id: str,
) -> SatelliteRainfall | None:
    return database.scalar(
        select(SatelliteRainfall)
        .where(SatelliteRainfall.location_id == location_id)
        .order_by(
            SatelliteRainfall.period_end.desc(),
            SatelliteRainfall.id.desc(),
        )
        .limit(1)
    )


def _normalize_location_or_404(location_id: str) -> str:
    try:
        key, _ = satellite_collector.normalize_location(location_id)
        return key
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.get("/health")
def satellite_health(
    database: Session = Depends(get_database),
):
    """Show provider configuration without exposing credentials."""

    latest = database.scalar(
        select(SatelliteRainfall)
        .order_by(
            SatelliteRainfall.period_end.desc(),
            SatelliteRainfall.id.desc(),
        )
        .limit(1)
    )

    return {
        **imerg_service.get_status(),
        "refresh_endpoint_protected": bool(
            os.getenv("SATELLITE_REFRESH_API_KEY", "").strip()
        ),
        "latest_stored_observation": (
            latest.period_end
            if latest is not None
            else None
        ),
        "latest_stored_source_file": (
            latest.source_file
            if latest is not None
            else None
        ),
        "registration_url": (
            "https://registration.pps.eosdis.nasa.gov/"
        ),
    }


@router.post(
    "/refresh/{location_id}",
    response_model=SatelliteRefreshResponse,
)
async def refresh_satellite_location(
    location_id: str,
    force_provider_refresh: bool = False,
    _: None = Depends(_require_refresh_key),
    database: Session = Depends(get_database),
):
    """Download/sample the newest IMERG grid for one location."""

    try:
        return await satellite_collector.refresh_location(
            database,
            location_id,
            force_provider_refresh=force_provider_refresh,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except Exception as error:
        _raise_provider_http_error(error)


@router.post(
    "/refresh-all",
    response_model=SatelliteRefreshAllResponse,
)
async def refresh_all_satellite_locations(
    force_provider_refresh: bool = False,
    _: None = Depends(_require_refresh_key),
    database: Session = Depends(get_database),
):
    """Download once and sample all configured monitoring locations."""

    try:
        return await satellite_collector.refresh_all(
            database,
            force_provider_refresh=force_provider_refresh,
        )

    except Exception as error:
        _raise_provider_http_error(error)


@router.get(
    "/latest",
    response_model=list[SatelliteRainfallResponse],
)
def latest_satellite_rainfall_for_all_locations(
    database: Session = Depends(get_database),
):
    """Return the newest stored IMERG value for every location."""

    measurements = []

    for location_id in LIVE_LOCATIONS:
        latest = _latest_measurement(database, location_id)

        if latest is not None:
            measurements.append(latest)

    return measurements


@router.get(
    "/latest/{location_id}",
    response_model=SatelliteRainfallResponse,
)
def latest_satellite_rainfall_for_location(
    location_id: str,
    database: Session = Depends(get_database),
):
    """Return the newest stored IMERG value for one location."""

    key = _normalize_location_or_404(location_id)
    latest = _latest_measurement(database, key)

    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No NASA IMERG observation is stored for "
                f"{key}. Run the refresh endpoint first."
            ),
        )

    return latest


@router.get(
    "/history/{location_id}",
    response_model=list[SatelliteRainfallResponse],
)
def satellite_rainfall_history(
    location_id: str,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    database: Session = Depends(get_database),
):
    """Return stored IMERG history for a monitored location."""

    key = _normalize_location_or_404(location_id)

    return database.scalars(
        select(SatelliteRainfall)
        .where(SatelliteRainfall.location_id == key)
        .order_by(
            SatelliteRainfall.period_end.desc(),
            SatelliteRainfall.id.desc(),
        )
        .limit(limit)
    ).all()


@router.get(
    "/model-input/{location_id}",
    response_model=SatelliteModelInputResponse,
)
def satellite_rainfall_model_input(
    location_id: str,
    database: Session = Depends(get_database),
):
    """Return a freshness-checked value for the existing ML input."""

    key = _normalize_location_or_404(location_id)
    latest = _latest_measurement(database, key)

    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No NASA IMERG observation is stored for "
                f"{key}. Run the refresh endpoint first."
            ),
        )

    period_end = latest.period_end

    if period_end.tzinfo is None:
        period_end = period_end.replace(tzinfo=timezone.utc)

    age_hours = max(
        0.0,
        (
            datetime.now(timezone.utc)
            - period_end.astimezone(timezone.utc)
        ).total_seconds()
        / 3600.0,
    )
    is_fresh = age_hours <= imerg_service.max_data_age_hours
    usable = bool(
        is_fresh
        and not latest.is_missing
        and latest.rainfall_rate_mm_hr is not None
    )

    if latest.is_missing:
        freshness_status = "MISSING"
    elif is_fresh:
        freshness_status = "FRESH"
    else:
        freshness_status = "STALE"

    return {
        "location_id": key,
        "rainfall_mm_hr": (
            latest.rainfall_rate_mm_hr
            if usable
            else None
        ),
        "usable_for_prediction": usable,
        "freshness_status": freshness_status,
        "maximum_age_hours": imerg_service.max_data_age_hours,
        "quality_status": latest.quality_status,
        "provider": latest.provider,
        "product": latest.product,
        "product_version": latest.product_version,
        "source_file": latest.source_file,
        "observed_at": period_end,
        "data_age_hours": round(age_hours, 2),
        "warning": (
            "Satellite rainfall is supporting evidence. Keep ground "
            "rain gauges and weather observations in the sensor-fusion "
            "decision before issuing a public warning."
        ),
    }
