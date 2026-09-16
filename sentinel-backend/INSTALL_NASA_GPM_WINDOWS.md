# Install NASA GPM upgrade on Windows

This package is prepared for Git commit `2af39c0` of
`reenhajira-beep/Landslide-Risk-NER-` and preserves the existing vibration
feature.

Run all commands from:

```powershell
C:\Users\abira\OneDrive\Desktop\sih_project\sentinel-backend
```

## 1. Confirm a clean repository

```powershell
git status --short
```

The command must print nothing before the upgrade is installed.

## 2. Create a feature branch

```powershell
git switch -c feature/nasa-gpm-integration
```

## 3. Extract the ZIP into the backend folder

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\SENTINEL_NASA_GPM_upgrade_latest_20260916.zip" -DestinationPath . -Force
```

## 4. Install the additional dependency

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements-satellite.txt
```

## 5. Verify the code

```powershell
python -m py_compile .\app\main.py .\app\database\satellite_model.py .\app\schemas\satellite.py .\app\services\imerg_service.py .\app\services\satellite_collector.py .\app\routers\satellite.py
```

```powershell
python -m pytest .\tests\test_imerg_service.py .\tests\test_vibration_services.py -q
```

Expected result: `11 passed`.

## 6. Stage only the intended files

```powershell
git add -- app/main.py app/database/satellite_model.py app/routers/satellite.py app/schemas/__init__.py app/schemas/satellite.py app/services/imerg_service.py app/services/satellite_collector.py tests/test_imerg_service.py requirements-satellite.txt README_SATELLITE_SERVER.md .env.satellite.example INSTALL_NASA_GPM_WINDOWS.md
```

```powershell
git diff --cached --name-only
```

Never stage `.env`, `.venv`, passwords, or access keys.

## 7. Commit and push the feature branch

```powershell
git commit -m "Add NASA GPM IMERG satellite rainfall integration"
```

```powershell
git push -u origin feature/nasa-gpm-integration
```

## 8. Configure NASA access later

Read `README_SATELLITE_SERVER.md`. Copy only the required NASA settings from
`.env.satellite.example` into your local `.env`. Never commit `.env`.

