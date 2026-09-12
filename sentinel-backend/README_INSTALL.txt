SENTINEL-NER Vibration Fusion Upgrade
=====================================

Files in this package:

app/services/vibration_service.py
    Filters X/Y/Z samples, extracts vibration features and assesses movement.

app/services/sensor_fusion_service.py
    Combines the current environmental ML score with vibration evidence.

app/database/vibration_model.py
    Stores extracted vibration features in PostgreSQL.

app/routers/vibration.py
    Provides analyze, readings, thresholds and fusion-predict endpoints.

tests/test_vibration_services.py
    Tests frequency extraction, validation, anomaly separation and fusion.

The existing app/main.py already includes app.routers.vibration, so no main.py
change is required.

Optional .env calibration values:

VIBRATION_RMS_ABNORMAL_MPS2=0.08
VIBRATION_PEAK_ABNORMAL_MPS2=0.25
VIBRATION_TILT_ABNORMAL_DEG=0.75
SENSOR_FUSION_ENVIRONMENT_WEIGHT=0.75

These are prototype defaults. Calibrate them with sensor baselines and labelled
field observations before operational public-warning use.
