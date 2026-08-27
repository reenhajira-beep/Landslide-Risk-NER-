import httpx


OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
)


LIVE_LOCATIONS = {
    "GUWAHATI": {
        "latitude": 26.1445,
        "longitude": 91.7362,
        "tilt_deg": 18.0,
        "vegetation_change_pct": 12.0,
        "satellite_risk_index": 0.35,
    },

    "SHILLONG": {
        "latitude": 25.5788,
        "longitude": 91.8933,
        "tilt_deg": 34.0,
        "vegetation_change_pct": 22.0,
        "satellite_risk_index": 0.68,
    },

    "GANGTOK": {
        "latitude": 27.3389,
        "longitude": 88.6065,
        "tilt_deg": 41.0,
        "vegetation_change_pct": 28.0,
        "satellite_risk_index": 0.76,
    },

    "ITANAGAR": {
        "latitude": 27.0844,
        "longitude": 93.6053,
        "tilt_deg": 36.0,
        "vegetation_change_pct": 19.0,
        "satellite_risk_index": 0.63,
    },

    "KOHIMA": {
        "latitude": 25.6751,
        "longitude": 94.1086,
        "tilt_deg": 32.0,
        "vegetation_change_pct": 17.0,
        "satellite_risk_index": 0.58,
    },

    "IMPHAL": {
        "latitude": 24.8170,
        "longitude": 93.9368,
        "tilt_deg": 21.0,
        "vegetation_change_pct": 13.0,
        "satellite_risk_index": 0.42,
    },

    "AIZAWL": {
        "latitude": 23.7271,
        "longitude": 92.7176,
        "tilt_deg": 37.0,
        "vegetation_change_pct": 25.0,
        "satellite_risk_index": 0.69,
    },

    "AGARTALA": {
        "latitude": 23.8315,
        "longitude": 91.2868,
        "tilt_deg": 14.0,
        "vegetation_change_pct": 8.0,
        "satellite_risk_index": 0.29,
    },
}


async def fetch_live_weather(
    location_id: str,
) -> dict:

    key = (
        location_id
        .strip()
        .upper()
    )

    location = LIVE_LOCATIONS.get(
        key
    )

    if not location:
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

        weather_data = (
            response.json()
        )


    current = (
        weather_data.get(
            "current",
            {},
        )
    )


    temperature = float(
        current.get(
            "temperature_2m",
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


    humidity = float(
        current.get(
            "relative_humidity_2m",
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


    # Convert current precipitation into
    # the rainfall feature expected by your
    # existing model.
    rainfall_mm_hr = max(
        precipitation,
        rain,
    )


    # Demo soil-moisture approximation.
    #
    # Later you can replace this with
    # dedicated satellite/soil sensor data.
    soil_moisture_pct = (
        0.70 * humidity
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
            location[
                "tilt_deg"
            ],

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