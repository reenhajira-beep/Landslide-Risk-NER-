import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal
from app.data.monitoring_locations import LIVE_LOCATIONS
import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database.connection import (
    Base,
    SessionLocal,
    engine,
    get_database,
)
from app.database.models import (
    Alert,
    CommunityReport,
    LiveMonitoring,
    Prediction,
)
from app.services.model_service import model_service
from app.services.risk_agent import landslide_agent


# =========================================================
# LIVE WEATHER CONFIGURATION
# =========================================================

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Backend collection interval.
# 300 seconds = 5 minutes.
LIVE_COLLECTION_INTERVAL_SECONDS = 300


# =========================================================
# NORTH-EAST INDIA MONITORING LOCATIONS
#
# Weather:
#   LIVE from Open-Meteo.
#
# Terrain / GIS / satellite:
#   Prepared project values used as model inputs.
# =========================================================


# =========================================================
# PREDICTION SCHEMAS
# =========================================================

class PredictionInput(BaseModel):
    location_id: str = Field(
        min_length=1,
        max_length=100,
    )

    rainfall_mm_hr: float = Field(
        ge=0,
        le=500,
    )

    soil_moisture_pct: float = Field(
        ge=0,
        le=100,
    )

    tilt_deg: float = Field(
        ge=0,
        le=90,
    )

    vegetation_change_pct: float = Field(
        ge=0,
        le=100,
    )

    satellite_risk_index: float = Field(
        ge=0,
        le=1,
    )


class PredictionRecordResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    location_id: str
    rainfall_mm_hr: float
    soil_moisture_pct: float
    tilt_deg: float
    vegetation_change_pct: float
    satellite_risk_index: float
    risk_score: float
    risk_level: str
    alert_generated: bool
    model_used: str
    predicted_at: datetime


class AgentPredictionResponse(
    PredictionRecordResponse
):
    alert_id: int | None = None
    agent_status: str
    contributing_factors: list[str]
    recommended_actions: list[str]
    analysis_message: str


# =========================================================
# ALERT SCHEMA
# =========================================================

class AlertResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    prediction_id: int
    location_id: str
    risk_score: float
    risk_level: str
    message: str
    status: str
    created_at: datetime
    acknowledged_at: datetime | None


# =========================================================
# COMMUNITY REPORT SCHEMAS
# =========================================================

ReportType = Literal[
    "SOIL_CRACK",
    "ROCKFALL",
    "WATER_SEEPAGE",
    "GROUND_MOVEMENT",
    "OTHER",
]

ReportSeverity = Literal[
    "LOW",
    "MODERATE",
    "HIGH",
    "CRITICAL",
]

ReportStatus = Literal[
    "PENDING",
    "VERIFIED",
    "RESOLVED",
    "REJECTED",
]


class CommunityReportInput(BaseModel):
    location_id: str = Field(
        min_length=1,
        max_length=100,
    )

    report_type: ReportType

    description: str = Field(
        min_length=5,
        max_length=2000,
    )

    severity: ReportSeverity = "MODERATE"

    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
    )

    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
    )

    reporter_name: str | None = Field(
        default=None,
        max_length=100,
    )


class CommunityReportResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    location_id: str
    report_type: str
    description: str
    severity: str
    latitude: float | None
    longitude: float | None
    reporter_name: str | None
    status: str
    reported_at: datetime
    reviewed_at: datetime | None


class CommunityReportStatusUpdate(BaseModel):
    status: ReportStatus


# =========================================================
# FETCH LIVE WEATHER
# =========================================================

async def fetch_live_weather(
    location_id: str,
) -> dict:

    key = (
        location_id
        .strip()
        .upper()
    )

    location = LIVE_LOCATIONS.get(key)

    if location is None:
        raise ValueError(
            f"Unknown monitoring location: {location_id}"
        )

    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],

        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "rain,"
            "wind_speed_10m"
        ),

        "timezone": "Asia/Kolkata",
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

    # -----------------------------------------------------
    # DEMO SOIL-MOISTURE ESTIMATE
    #
    # Until a real soil-moisture sensor/API is connected,
    # estimate soil moisture using humidity + rainfall.
    # -----------------------------------------------------

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
            current.get("time"),
    }


# =========================================================
# CALCULATE LIVE LANDSLIDE RISK
# =========================================================

async def calculate_live_risk(
    location_id: str,
) -> dict:

    live_data = await fetch_live_weather(
        location_id
    )

    agent_result = landslide_agent.analyze(
        rainfall_mm_hr=(
            live_data["rainfall_mm_hr"]
        ),

        soil_moisture_pct=(
            live_data["soil_moisture_pct"]
        ),

        tilt_deg=(
            live_data["tilt_deg"]
        ),

        vegetation_change_pct=(
            live_data[
                "vegetation_change_pct"
            ]
        ),

        satellite_risk_index=(
            live_data[
                "satellite_risk_index"
            ]
        ),
    )

    return {
        **live_data,

        "risk_score":
            agent_result["risk_score"],

        "risk_level":
            agent_result["risk_level"],

        "alert_generated":
            agent_result["alert_generated"],

        "agent_status":
            agent_result["agent_status"],

        "contributing_factors":
            agent_result[
                "contributing_factors"
            ],

        "recommended_actions":
            agent_result[
                "recommended_actions"
            ],

        "analysis_message":
            agent_result[
                "analysis_message"
            ],
    }


# =========================================================
# SAVE LIVE SNAPSHOT TO POSTGRESQL
# =========================================================

def save_live_snapshot(
    live_data: dict,
) -> None:

    database = SessionLocal()

    try:
        record = LiveMonitoring(
            location_id=(
                live_data["location_id"]
            ),

            location_name=(
                live_data["location_name"]
            ),

            state=(
                live_data["state"]
            ),

            latitude=(
                live_data["latitude"]
            ),

            longitude=(
                live_data["longitude"]
            ),

            temperature_c=(
                live_data["temperature_c"]
            ),

            rainfall_mm_hr=(
                live_data["rainfall_mm_hr"]
            ),

            relative_humidity_pct=(
                live_data[
                    "relative_humidity_pct"
                ]
            ),

            wind_speed_kmh=(
                live_data["wind_speed_kmh"]
            ),

            soil_moisture_pct=(
                live_data[
                    "soil_moisture_pct"
                ]
            ),

            tilt_deg=(
                live_data["tilt_deg"]
            ),

            vegetation_change_pct=(
                live_data[
                    "vegetation_change_pct"
                ]
            ),

            satellite_risk_index=(
                live_data[
                    "satellite_risk_index"
                ]
            ),

            risk_score=(
                live_data["risk_score"]
            ),

            risk_level=(
                live_data["risk_level"]
            ),

            alert_generated=(
                live_data["alert_generated"]
            ),

            weather_time=(
                live_data.get(
                    "weather_time"
                )
            ),
        )

        database.add(record)

        database.commit()

    except Exception:
        database.rollback()
        raise

    finally:
        database.close()


# =========================================================
# COLLECT ALL 8 LOCATIONS
# =========================================================

async def collect_all_live_locations():
    print(
        "[SENTINEL] Starting live collection..."
    )

    location_ids = list(
        LIVE_LOCATIONS.keys()
    )

    # Fetch all locations concurrently.
    tasks = [
        calculate_live_risk(
            location_id
        )
        for location_id
        in location_ids
    ]

    results = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    saved_count = 0

    for location_id, result in zip(
        location_ids,
        results,
    ):

        if isinstance(
            result,
            Exception,
        ):
            print(
                "[LIVE ERROR]",
                location_id,
                repr(result),
            )

            continue

        try:
            save_live_snapshot(
                result
            )

            saved_count += 1

            print(
                "[LIVE SAVED]",
                result["location_id"],
                "| Temp:",
                result["temperature_c"],
                "| Rain:",
                result["rainfall_mm_hr"],
                "| Humidity:",
                result[
                    "relative_humidity_pct"
                ],
                "| Risk:",
                result["risk_level"],
                "| Score:",
                result["risk_score"],
            )

        except Exception as error:
            print(
                "[DATABASE ERROR]",
                location_id,
                repr(error),
            )

    print(
        "[SENTINEL] Collection complete:",
        f"{saved_count}/{len(location_ids)}",
        "locations stored.",
    )


# =========================================================
# AUTOMATIC 5-MINUTE COLLECTION LOOP
# =========================================================

async def live_monitoring_loop():

    while True:

        try:
            await collect_all_live_locations()

        except asyncio.CancelledError:
            raise

        except Exception as error:
            print(
                "[LIVE MONITORING ERROR]",
                repr(error),
            )

        print(
            "[SENTINEL] Next collection in 5 minutes."
        )

        await asyncio.sleep(
            LIVE_COLLECTION_INTERVAL_SECONDS
        )


# =========================================================
# STARTUP / SHUTDOWN
# =========================================================

@asynccontextmanager
async def lifespan(
    application: FastAPI,
):

    # Ensure database tables exist.
    Base.metadata.create_all(
        bind=engine
    )

    # Load trained ML model.
    model_service.load_model()

    # Start automatic live collector.
    collector_task = asyncio.create_task(
        live_monitoring_loop()
    )

    print(
        "[SENTINEL] Automatic live monitoring started."
    )

    try:
        yield

    finally:
        collector_task.cancel()

        try:
            await collector_task

        except asyncio.CancelledError:
            pass

        print(
            "[SENTINEL] Live monitoring stopped."
        )


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="SENTINEL-NER API",

    description=(
        "AI-powered landslide prediction, "
        "automatic live weather monitoring, "
        "early warning and community reporting API."
    ),

    version="3.0.0",

    lifespan=lifespan,
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",

        "http://localhost:5174",
        "http://127.0.0.1:5174",

        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "status": "ok",

        "message":
            "SENTINEL-NER backend is running",

        "version":
            "3.0.0",

        "live_monitoring":
            True,

        "collection_interval_seconds":
            LIVE_COLLECTION_INTERVAL_SECONDS,

        "monitoring_locations":
            len(LIVE_LOCATIONS),

        "docs":
            "/docs",
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/api/v1/health")
def health_check():

    return {
        "status":
            "healthy",

        "service":
            "SENTINEL-NER Backend",

        "agent":
            "LandslideRiskAgent",

        "live_weather":
            "enabled",

        "automatic_collection":
            "enabled",

        "collection_interval_seconds":
            LIVE_COLLECTION_INTERVAL_SECONDS,
    }


@app.get("/api/v1/database-health")
def database_health_check():

    with engine.connect() as connection:

        database_name = connection.execute(
            text(
                "SELECT current_database()"
            )
        ).scalar_one()

    return {
        "status":
            "connected",

        "database":
            database_name,
    }


@app.get("/api/v1/model-health")
def model_health_check():

    return model_service.get_status()


# =========================================================
# AVAILABLE LIVE LOCATIONS
# =========================================================

@app.get("/api/v1/live-locations")
def get_live_locations():

    return [
        {
            "location_id":
                location_id,

            "name":
                data["name"],

            "state":
                data["state"],

            "latitude":
                data["latitude"],

            "longitude":
                data["longitude"],
        }

        for location_id, data
        in LIVE_LOCATIONS.items()
    ]


# =========================================================
# ONE LOCATION LIVE WEATHER
# =========================================================

@app.get(
    "/api/v1/live-weather/{location_id}"
)
async def live_weather(
    location_id: str,
):

    try:
        return await fetch_live_weather(
            location_id
        )

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except httpx.HTTPError as error:

        raise HTTPException(
            status_code=502,
            detail=(
                "Live weather server unavailable: "
                f"{str(error)}"
            ),
        )


# =========================================================
# ONE LOCATION LIVE RISK
# =========================================================

@app.get(
    "/api/v1/live-risk/{location_id}"
)
async def live_risk(
    location_id: str,
):

    try:
        return await calculate_live_risk(
            location_id
        )

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except httpx.HTTPError as error:

        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to retrieve live weather: "
                f"{str(error)}"
            ),
        )


# =========================================================
# ALL LOCATIONS - DIRECT LIVE RISK
#
# Directly requests fresh server data.
# =========================================================

@app.get("/api/v1/live-risk")
async def get_all_live_risks():

    location_ids = list(
        LIVE_LOCATIONS.keys()
    )

    tasks = [
        calculate_live_risk(
            location_id
        )

        for location_id
        in location_ids
    ]

    results = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    response = []

    for location_id, result in zip(
        location_ids,
        results,
    ):

        if isinstance(
            result,
            Exception,
        ):

            response.append({
                "location_id":
                    location_id,

                "status":
                    "unavailable",

                "error":
                    str(result),
            })

        else:
            response.append(
                result
            )

    return response


# =========================================================
# LATEST STORED LIVE MONITORING
#
# THIS is the endpoint the final map should use.
# =========================================================

@app.get(
    "/api/v1/live-monitoring/latest"
)
def get_latest_live_monitoring(
    database: Session = Depends(
        get_database
    ),
):

    response = []

    for location_id in LIVE_LOCATIONS.keys():

        query = (
            select(LiveMonitoring)
            .where(
                LiveMonitoring.location_id
                == location_id
            )
            .order_by(
                LiveMonitoring
                .collected_at
                .desc()
            )
            .limit(1)
        )

        latest = database.scalar(
            query
        )

        if latest is None:
            continue

        response.append({
            "id":
                latest.id,

            "location_id":
                latest.location_id,

            "location_name":
                latest.location_name,

            "state":
                latest.state,

            "latitude":
                latest.latitude,

            "longitude":
                latest.longitude,

            "temperature_c":
                latest.temperature_c,

            "rainfall_mm_hr":
                latest.rainfall_mm_hr,

            "relative_humidity_pct":
                latest.relative_humidity_pct,

            "wind_speed_kmh":
                latest.wind_speed_kmh,

            "soil_moisture_pct":
                latest.soil_moisture_pct,

            "tilt_deg":
                latest.tilt_deg,

            "vegetation_change_pct":
                latest.vegetation_change_pct,

            "satellite_risk_index":
                latest.satellite_risk_index,

            "risk_score":
                latest.risk_score,

            "risk_level":
                latest.risk_level,

            "alert_generated":
                latest.alert_generated,

            "weather_time":
                latest.weather_time,

            "collected_at":
                latest.collected_at,
        })

    return response


# =========================================================
# LIVE MONITORING HISTORY
# =========================================================

@app.get(
    "/api/v1/live-monitoring/history/{location_id}"
)
def get_live_monitoring_history(
    location_id: str,

    database: Session = Depends(
        get_database
    ),
):

    key = (
        location_id
        .strip()
        .upper()
    )

    if key not in LIVE_LOCATIONS:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown monitoring location: "
                f"{location_id}"
            ),
        )

    query = (
        select(LiveMonitoring)
        .where(
            LiveMonitoring.location_id
            == key
        )
        .order_by(
            LiveMonitoring
            .collected_at
            .desc()
        )
        .limit(100)
    )

    rows = database.scalars(
        query
    ).all()

    return [
        {
            "id":
                row.id,

            "location_id":
                row.location_id,

            "location_name":
                row.location_name,

            "state":
                row.state,

            "latitude":
                row.latitude,

            "longitude":
                row.longitude,

            "temperature_c":
                row.temperature_c,

            "rainfall_mm_hr":
                row.rainfall_mm_hr,

            "relative_humidity_pct":
                row.relative_humidity_pct,

            "wind_speed_kmh":
                row.wind_speed_kmh,

            "soil_moisture_pct":
                row.soil_moisture_pct,

            "tilt_deg":
                row.tilt_deg,

            "vegetation_change_pct":
                row.vegetation_change_pct,

            "satellite_risk_index":
                row.satellite_risk_index,

            "risk_score":
                row.risk_score,

            "risk_level":
                row.risk_level,

            "alert_generated":
                row.alert_generated,

            "weather_time":
                row.weather_time,

            "collected_at":
                row.collected_at,
        }

        for row in rows
    ]


# =========================================================
# MANUAL LANDSLIDE PREDICTION
# =========================================================

@app.post(
    "/api/v1/predict",
    response_model=AgentPredictionResponse,
)
def predict_landslide(
    data: PredictionInput,

    database: Session = Depends(
        get_database
    ),
):

    agent_result = landslide_agent.analyze(
        rainfall_mm_hr=(
            data.rainfall_mm_hr
        ),

        soil_moisture_pct=(
            data.soil_moisture_pct
        ),

        tilt_deg=(
            data.tilt_deg
        ),

        vegetation_change_pct=(
            data.vegetation_change_pct
        ),

        satellite_risk_index=(
            data.satellite_risk_index
        ),
    )

    prediction = Prediction(
        location_id=(
            data.location_id
            .strip()
            .upper()
        ),

        rainfall_mm_hr=(
            data.rainfall_mm_hr
        ),

        soil_moisture_pct=(
            data.soil_moisture_pct
        ),

        tilt_deg=(
            data.tilt_deg
        ),

        vegetation_change_pct=(
            data.vegetation_change_pct
        ),

        satellite_risk_index=(
            data.satellite_risk_index
        ),

        risk_score=(
            agent_result["risk_score"]
        ),

        risk_level=(
            agent_result["risk_level"]
        ),

        alert_generated=(
            agent_result[
                "alert_generated"
            ]
        ),

        model_used=(
            agent_result["model_used"]
        ),
    )

    database.add(
        prediction
    )

    database.flush()

    alert = None

    if agent_result[
        "alert_generated"
    ]:

        alert = Alert(
            prediction_id=(
                prediction.id
            ),

            location_id=(
                prediction.location_id
            ),

            risk_score=(
                prediction.risk_score
            ),

            risk_level=(
                prediction.risk_level
            ),

            message=(
                f"{prediction.risk_level} "
                "landslide risk detected "
                f"at {prediction.location_id}. "
                "Risk score: "
                f"{prediction.risk_score}."
            ),

            status="ACTIVE",
        )

        database.add(
            alert
        )

    database.commit()

    database.refresh(
        prediction
    )

    if alert is not None:
        database.refresh(
            alert
        )

    return {
        "id":
            prediction.id,

        "location_id":
            prediction.location_id,

        "rainfall_mm_hr":
            prediction.rainfall_mm_hr,

        "soil_moisture_pct":
            prediction.soil_moisture_pct,

        "tilt_deg":
            prediction.tilt_deg,

        "vegetation_change_pct":
            prediction.vegetation_change_pct,

        "satellite_risk_index":
            prediction.satellite_risk_index,

        "risk_score":
            prediction.risk_score,

        "risk_level":
            prediction.risk_level,

        "alert_generated":
            prediction.alert_generated,

        "model_used":
            prediction.model_used,

        "predicted_at":
            prediction.predicted_at,

        "alert_id":
            (
                alert.id
                if alert is not None
                else None
            ),

        "agent_status":
            agent_result[
                "agent_status"
            ],

        "contributing_factors":
            agent_result[
                "contributing_factors"
            ],

        "recommended_actions":
            agent_result[
                "recommended_actions"
            ],

        "analysis_message":
            agent_result[
                "analysis_message"
            ],
    }


# =========================================================
# PREDICTION HISTORY
# =========================================================

@app.get(
    "/api/v1/predictions",

    response_model=list[
        PredictionRecordResponse
    ],
)
def get_prediction_history(
    database: Session = Depends(
        get_database
    ),
):

    query = (
        select(Prediction)
        .order_by(
            Prediction.id.desc()
        )
        .limit(100)
    )

    return database.scalars(
        query
    ).all()


# =========================================================
# ALERTS
# =========================================================

@app.get(
    "/api/v1/alerts",

    response_model=list[
        AlertResponse
    ],
)
def get_alerts(
    active_only: bool = True,

    database: Session = Depends(
        get_database
    ),
):

    query = (
        select(Alert)
        .order_by(
            Alert.id.desc()
        )
    )

    if active_only:

        query = query.where(
            Alert.status == "ACTIVE"
        )

    return database.scalars(
        query
    ).all()


@app.patch(
    "/api/v1/alerts/{alert_id}/acknowledge",

    response_model=AlertResponse,
)
def acknowledge_alert(
    alert_id: int,

    database: Session = Depends(
        get_database
    ),
):

    alert = database.get(
        Alert,
        alert_id,
    )

    if alert is None:

        raise HTTPException(
            status_code=404,
            detail="Alert not found",
        )

    alert.status = "ACKNOWLEDGED"

    alert.acknowledged_at = (
        datetime.now(
            timezone.utc
        )
    )

    database.commit()

    database.refresh(
        alert
    )

    return alert


# =========================================================
# CREATE COMMUNITY REPORT
# =========================================================

@app.post(
    "/api/v1/community-reports",

    response_model=CommunityReportResponse,

    status_code=201,
)
def create_community_report(
    data: CommunityReportInput,

    database: Session = Depends(
        get_database
    ),
):

    report = CommunityReport(
        location_id=(
            data.location_id
            .strip()
            .upper()
        ),

        report_type=(
            data.report_type
        ),

        description=(
            data.description
            .strip()
        ),

        severity=(
            data.severity
        ),

        latitude=(
            data.latitude
        ),

        longitude=(
            data.longitude
        ),

        reporter_name=(
            data.reporter_name.strip()
            if data.reporter_name
            else None
        ),

        status="PENDING",
    )

    database.add(
        report
    )

    database.commit()

    database.refresh(
        report
    )

    return report


# =========================================================
# GET COMMUNITY REPORTS
# =========================================================

@app.get(
    "/api/v1/community-reports",

    response_model=list[
        CommunityReportResponse
    ],
)
def get_community_reports(
    status: ReportStatus | None = None,

    location_id: str | None = None,

    database: Session = Depends(
        get_database
    ),
):

    query = select(
        CommunityReport
    )

    if status is not None:

        query = query.where(
            CommunityReport.status
            == status
        )

    if location_id is not None:

        query = query.where(
            CommunityReport.location_id
            == location_id
            .strip()
            .upper()
        )

    query = (
        query
        .order_by(
            CommunityReport.id.desc()
        )
        .limit(100)
    )

    return database.scalars(
        query
    ).all()


# =========================================================
# UPDATE COMMUNITY REPORT STATUS
# =========================================================

@app.patch(
    "/api/v1/community-reports/{report_id}/status",

    response_model=CommunityReportResponse,
)
def update_community_report_status(
    report_id: int,

    data: CommunityReportStatusUpdate,

    database: Session = Depends(
        get_database
    ),
):

    report = database.get(
        CommunityReport,
        report_id,
    )

    if report is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Community report not found"
            ),
        )

    report.status = data.status

    report.reviewed_at = (
        datetime.now(
            timezone.utc
        )
    )

    database.commit()

    database.refresh(
        report
    )

    return report