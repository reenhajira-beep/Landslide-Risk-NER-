# SENTINEL-NER NASA GPM IMERG Data Server

This upgrade adds real NASA GPM IMERG Early Run satellite rainfall to the
existing FastAPI backend without replacing the prediction, live-weather,
vibration, sensor-fusion, alert, or community-report modules.

## What the server does

1. Authenticates to the official NASA PPS HTTPS archive.
2. Finds the newest 30-minute IMERG Early Run GIS product.
3. Downloads the global ZIP only once and keeps a short memory cache.
4. Reads the total-precipitation GeoTIFF without requiring GDAL/Rasterio.
5. Samples the documented 0.1-degree grid for every monitored location.
6. Converts the 30-minute accumulation into an average `mm/hr` value.
7. Stores only point measurements and source metadata in PostgreSQL.
8. Rejects missing or stale values from the ML-ready endpoint.

NASA describes Early Run as a 30-minute, approximately 10 km product with
roughly 4-5 hours of latency. It is supporting evidence and should be fused
with ground rain gauges, weather observations, soil, tilt, and vibration.

## Files added

```text
app/database/satellite_model.py
app/routers/satellite.py
app/schemas/satellite.py
app/services/imerg_service.py
app/services/satellite_collector.py
tests/test_imerg_service.py
.env.satellite.example
requirements-satellite.txt
```

`app/main.py` is updated to include the router and optional automatic
collector. API version is now `3.2.0`.

## 1. Register for NASA PPS access

Open this official page and register an email address:

https://registration.pps.eosdis.nasa.gov/

NASA's IMERG GIS documentation currently says to use the registered email as
both the HTTPS username and password. Registration may require time to become
active.

## 2. Install the satellite dependency

Open PowerShell in `sentinel-backend` and run:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements-satellite.txt
```

## 3. Add settings to the existing `.env`

Do not remove your database or JWT values. Add these lines at the bottom:

```env
NASA_GPM_ENABLED=true
NASA_GPM_PPS_EMAIL=YOUR_REGISTERED_EMAIL
NASA_GPM_PPS_PASSWORD=
NASA_GPM_AUTO_COLLECTION=true
NASA_GPM_COLLECTION_INTERVAL_SECONDS=1800
NASA_GPM_CACHE_TTL_SECONDS=900
NASA_GPM_TIMEOUT_SECONDS=45
NASA_GPM_MAX_DATA_AGE_HOURS=12
NASA_GPM_MAX_DOWNLOAD_MB=64
NASA_GPM_MAX_UNCOMPRESSED_MB=64
SATELLITE_REFRESH_API_KEY=
```

Replace only `YOUR_REGISTERED_EMAIL`. Do not share or commit `.env`.

For additional protection, generate a refresh key:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Put the generated value after `SATELLITE_REFRESH_API_KEY=`. Do not paste that
key into chat or GitHub.

## 4. Verify files and offline tests

```powershell
python -m py_compile .\app\main.py .\app\database\satellite_model.py .\app\schemas\satellite.py .\app\services\imerg_service.py .\app\services\satellite_collector.py .\app\routers\satellite.py
python -m pytest .\tests\test_imerg_service.py -q
```

Expected test result:

```text
6 passed
```

The tests do not contact NASA and do not require credentials.

## 5. Start the backend

```powershell
python -m uvicorn app.main:app --reload --reload-dir app --host 127.0.0.1 --port 8000
```

Using `--reload-dir app` prevents WatchFiles from monitoring `.venv`.

## 6. Check provider health

In a second PowerShell terminal:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/satellite/health" | ConvertTo-Json -Depth 5
```

Correct configured status:

```json
{
  "status": "ready",
  "enabled": true,
  "configured": true,
  "credentials_exposed": false
}
```

If the email is not yet configured, the backend still starts normally and
the endpoint returns `"status": "not_configured"`.

## 7. Fetch satellite rainfall

Without a refresh key:

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/v1/satellite/refresh-all" | ConvertTo-Json -Depth 8
```

If `SATELLITE_REFRESH_API_KEY` is set:

```powershell
$headers = @{ "X-Satellite-Refresh-Key" = "YOUR_PRIVATE_KEY" }
Invoke-RestMethod -Method Post -Headers $headers "http://127.0.0.1:8000/api/v1/satellite/refresh-all" | ConvertTo-Json -Depth 8
```

The first successful request creates rows. Repeating it for the same NASA
file returns those rows without inserting duplicates.

## API routes

```text
GET  /api/v1/satellite/health
POST /api/v1/satellite/refresh-all
POST /api/v1/satellite/refresh/{location_id}
GET  /api/v1/satellite/latest
GET  /api/v1/satellite/latest/{location_id}
GET  /api/v1/satellite/history/{location_id}?limit=100
GET  /api/v1/satellite/model-input/{location_id}
```

Examples:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/satellite/latest/GUWAHATI" | ConvertTo-Json
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/satellite/model-input/GUWAHATI" | ConvertTo-Json
```

The ML-ready endpoint returns `usable_for_prediction=false` when the pixel is
missing or older than `NASA_GPM_MAX_DATA_AGE_HOURS`. This prevents silent use
of invalid satellite values.

## Common responses

| Code | Meaning | Fix |
| --- | --- | --- |
| `200` | Request succeeded | No action needed |
| `401` | Wrong optional refresh key | Send the correct private header |
| `404` | Unknown location or no stored reading | Use a listed location or refresh first |
| `502` | NASA authentication/provider/product problem | Verify PPS registration and internet access |
| `503` | NASA integration is disabled or not configured | Check the `.env` values and restart Uvicorn |

## Important scientific limit

IMERG is satellite-estimated rainfall at approximately 10 km resolution and
has provider latency. It must not be described as a local real-time rain gauge
or used alone to issue evacuation warnings. Validate the complete landslide
model with labelled NER events and retain human/authority review.
