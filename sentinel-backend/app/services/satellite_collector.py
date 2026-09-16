"""Coordinates IMERG downloads, location sampling, and persistence."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.monitoring_locations import LIVE_LOCATIONS
from app.database.connection import SessionLocal
from app.database.satellite_model import SatelliteRainfall
from app.services.imerg_service import (
    IMERGGrid,
    imerg_service,
)


logger = logging.getLogger(__name__)


class SatelliteRainfallCollector:
    """Collect one IMERG product and persist point values idempotently."""

    def __init__(self) -> None:
        self._collection_lock = asyncio.Lock()

    @staticmethod
    def normalize_location(location_id: str) -> tuple[str, dict]:
        key = location_id.strip().upper()
        location = LIVE_LOCATIONS.get(key)

        if location is None:
            raise ValueError(
                f"Unknown monitoring location: {location_id}"
            )

        return key, location

    @staticmethod
    def _measurement_values(
        grid: IMERGGrid,
        location_id: str,
        location: dict,
    ) -> dict:
        sample = imerg_service.sample_grid(
            grid,
            latitude=float(location["latitude"]),
            longitude=float(location["longitude"]),
        )

        now = datetime.now(timezone.utc)
        latency_minutes = max(
            0.0,
            (now - grid.product.period_end).total_seconds() / 60.0,
        )

        return {
            "location_id": location_id,
            "location_name": location["name"],
            "state": location["state"],
            "latitude": float(location["latitude"]),
            "longitude": float(location["longitude"]),
            "provider": "NASA_GPM_PPS",
            "product": "IMERG_EARLY_GIS_30MIN",
            "product_version": grid.product.version,
            "source_file": grid.product.filename,
            "period_start": grid.product.period_start,
            "period_end": grid.product.period_end,
            "accumulation_mm": sample.accumulation_mm,
            "rainfall_rate_mm_hr": sample.rainfall_rate_mm_hr,
            "raw_pixel_value": sample.raw_pixel_value,
            "grid_row": sample.grid_row,
            "grid_column": sample.grid_column,
            "resolution_degrees": 0.1,
            "data_latency_minutes": round(latency_minutes, 2),
            "quality_status": sample.quality_status,
            "is_missing": sample.is_missing,
        }

    @staticmethod
    def _get_or_create(
        database: Session,
        values: dict,
    ) -> tuple[SatelliteRainfall, bool]:
        existing = database.scalar(
            select(SatelliteRainfall).where(
                SatelliteRainfall.location_id
                == values["location_id"],
                SatelliteRainfall.source_file
                == values["source_file"],
            )
        )

        if existing is not None:
            return existing, False

        measurement = SatelliteRainfall(**values)
        database.add(measurement)
        database.flush()

        return measurement, True

    async def refresh_location(
        self,
        database: Session,
        location_id: str,
        *,
        force_provider_refresh: bool = False,
    ) -> dict:
        key, location = self.normalize_location(location_id)

        async with self._collection_lock:
            grid = await imerg_service.fetch_latest_grid(
                force_refresh=force_provider_refresh,
            )
            values = self._measurement_values(
                grid,
                key,
                location,
            )

            try:
                measurement, created = self._get_or_create(
                    database,
                    values,
                )
                database.commit()
                database.refresh(measurement)
            except Exception:
                database.rollback()
                raise

        return {
            "status": "collected" if created else "already_current",
            "created": created,
            "measurement": measurement,
        }

    async def refresh_all(
        self,
        database: Session,
        *,
        force_provider_refresh: bool = False,
    ) -> dict:
        async with self._collection_lock:
            grid = await imerg_service.fetch_latest_grid(
                force_refresh=force_provider_refresh,
            )

            measurements: list[SatelliteRainfall] = []
            created_count = 0
            existing_count = 0
            missing_count = 0

            try:
                for location_id, location in LIVE_LOCATIONS.items():
                    values = self._measurement_values(
                        grid,
                        location_id,
                        location,
                    )
                    measurement, created = self._get_or_create(
                        database,
                        values,
                    )
                    measurements.append(measurement)

                    if created:
                        created_count += 1
                    else:
                        existing_count += 1

                    if measurement.is_missing:
                        missing_count += 1

                database.commit()

                for measurement in measurements:
                    database.refresh(measurement)

            except Exception:
                database.rollback()
                raise

        return {
            "status": "collection_complete",
            "source_file": grid.product.filename,
            "period_end": grid.product.period_end,
            "location_count": len(measurements),
            "created_count": created_count,
            "existing_count": existing_count,
            "missing_count": missing_count,
            "measurements": measurements,
        }


satellite_collector = SatelliteRainfallCollector()


async def satellite_collection_loop() -> None:
    """Refresh all configured locations at a controlled interval."""

    while True:
        database = SessionLocal()

        try:
            result = await satellite_collector.refresh_all(database)
            logger.info(
                "NASA IMERG collection complete: source=%s created=%s "
                "existing=%s missing=%s",
                result["source_file"],
                result["created_count"],
                result["existing_count"],
                result["missing_count"],
            )

        except asyncio.CancelledError:
            raise

        except Exception as error:
            logger.exception(
                "NASA IMERG automatic collection failed: %s",
                error,
            )

        finally:
            database.close()

        await asyncio.sleep(
            imerg_service.collection_interval_seconds
        )
