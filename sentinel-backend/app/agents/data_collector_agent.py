from typing import Any

import httpx

from app.data.monitoring_locations import LIVE_LOCATIONS


OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
)


class DataCollectorAgent:
    """
    Agent 1: Data Collector Agent

    Responsibilities:
    - Read the monitoring location from the shared dataset.
    - Fetch live weather data.
    - Validate and normalize values.
    - Combine weather with GIS/satellite inputs.
    """

    async def collect(
        self,
        location_id: str,
    ) -> dict[str, Any]:

        key = (
            location_id
            .strip()
            .upper()
        )

        location = LIVE_LOCATIONS.get(
            key
        )

        if location is None:
            raise ValueError(
                f"Unknown location: {location_id}"
            )

        params = {
            "latitude":
                location["latitude"],

            "longitude":
                location["longitude"],

            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "precipitation,"
                "rain,"
                "wind_speed_10m"
            ),

            "timezone":
                "Asia/Kolkata",
        }

        async with httpx.AsyncClient(
            timeout=20.0
        ) as client:

            response = await client.get(
                OPEN_METEO_URL,
                params=params,
            )

            response.raise_for_status()

            payload = response.json()

        current = payload.get(
            "current",
            {},
        )

        temperature = float(
            current.get(
                "temperature_2m",
                0,
            )
            or 0
        )

        humidity = float(
            current.get(
                "relative_humidity_2m",
                0,
            )
            or 0
        )

        precipitation = float(
            current.get(
                "precipitation",
                0,
            )
            or 0
        )

        rain = float(
            current.get(
                "rain",
                0,
            )
            or 0
        )

        wind_speed = float(
            current.get(
                "wind_speed_10m",
                0,
            )
            or 0
        )

        rainfall_mm_hr = max(
            precipitation,
            rain,
        )

        # Temporary soil moisture estimate
        # until real soil-moisture data is connected.
        soil_moisture_pct = (
            humidity * 0.70
            +
            min(
                rainfall_mm_hr * 8,
                30,
            )
        )

        soil_moisture_pct = max(
            0,
            min(
                soil_moisture_pct,
                100,
            ),
        )

        return {
            "location_id":
                key,

            "location_name":
                location["name"],

            "state":
                location["state"],

            "latitude":
                location["latitude"],

            "longitude":
                location["longitude"],

            "temperature_c":
                round(
                    temperature,
                    2,
                ),

            "rainfall_mm_hr":
                round(
                    rainfall_mm_hr,
                    2,
                ),

            "relative_humidity_pct":
                round(
                    humidity,
                    2,
                ),

            "wind_speed_kmh":
                round(
                    wind_speed,
                    2,
                ),

            "soil_moisture_pct":
                round(
                    soil_moisture_pct,
                    2,
                ),

            "tilt_deg":
                location["tilt_deg"],

            "vegetation_change_pct":
                location[
                    "vegetation_change_pct"
                ],

            "satellite_risk_index":
                location[
                    "satellite_risk_index"
                ],

            "weather_time":
                current.get(
                    "time"
                ),
        }


data_collector_agent = (
    DataCollectorAgent()
)