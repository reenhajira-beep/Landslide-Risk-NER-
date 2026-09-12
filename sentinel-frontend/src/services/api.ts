const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";


async function request<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(
    `${API_URL}${endpoint}`,
    {
      ...options,

      headers: {
        "Content-Type": "application/json",
        ...(options?.headers || {}),
      },
    },
  );

  if (!response.ok) {
    const errorText =
      await response.text();

    throw new Error(
      `API error ${response.status}: ${errorText}`,
    );
  }

  return response.json();
}


/* =========================================================
   HEALTH
========================================================= */

export async function getHealth() {
  return request(
    "/api/v1/health",
  );
}


export async function getDatabaseHealth() {
  return request(
    "/api/v1/database-health",
  );
}


export async function getModelHealth() {
  return request(
    "/api/v1/model-health",
  );
}


/* =========================================================
   LIVE MONITORING
========================================================= */

export type LiveMonitoringData = {
  id: number;

  location_id: string;
  location_name: string;
  state: string;

  latitude: number;
  longitude: number;

  temperature_c: number;

  rainfall_mm_hr: number;

  relative_humidity_pct: number;

  wind_speed_kmh: number;

  soil_moisture_pct: number;

  tilt_deg: number;

  vegetation_change_pct: number;

  satellite_risk_index: number;

  risk_score: number;

  risk_level: string;

  alert_generated: boolean;

  weather_time:
    | string
    | null;

  collected_at: string;
};


export async function getLatestLiveMonitoring():
Promise<LiveMonitoringData[]> {
  return request<
    LiveMonitoringData[]
  >(
    "/api/v1/live-monitoring/latest",
  );
}


export async function getLiveMonitoringHistory(
  locationId: string,
) {
  return request(
    `/api/v1/live-monitoring/history/${encodeURIComponent(
      locationId,
    )}`,
  );
}


/* =========================================================
   LIVE RISK
========================================================= */

export async function getLiveRisks() {
  return request(
    "/api/v1/live-risk",
  );
}


export async function getLiveRisk(
  locationId: string,
) {
  return request(
    `/api/v1/live-risk/${encodeURIComponent(
      locationId,
    )}`,
  );
}


export async function getLiveLocations() {
  return request(
    "/api/v1/live-locations",
  );
}


/* =========================================================
   PREDICTIONS
========================================================= */

export type PredictionRecord = {
  id: number;
  location_id: string;
  rainfall_mm_hr: number;
  soil_moisture_pct: number;
  tilt_deg: number;
  vegetation_change_pct: number;
  satellite_risk_index: number;
  risk_score: number;
  risk_level: string;
  alert_generated: boolean;
  model_used: string;
  predicted_at: string;
};


export async function getPredictions():
Promise<PredictionRecord[]> {
  return request<PredictionRecord[]>(
    "/api/v1/predictions",
  );
}


export type PredictionInput = {
  location_id: string;

  rainfall_mm_hr: number;

  soil_moisture_pct: number;

  tilt_deg: number;

  vegetation_change_pct: number;

  satellite_risk_index: number;
};


export async function createPrediction(
  data: PredictionInput,
) {
  return request(
    "/api/v1/predict",
    {
      method: "POST",

      body:
        JSON.stringify(
          data,
        ),
    },
  );
}


/* =========================================================
   ALERTS
========================================================= */

export async function getAlerts() {
  return request(
    "/api/v1/alerts",
  );
}


export async function acknowledgeAlert(
  alertId: number,
) {
  return request(
    `/api/v1/alerts/${alertId}/acknowledge`,
    {
      method:
        "PATCH",
    },
  );
}


/* =========================================================
   COMMUNITY REPORTS
========================================================= */

export async function getCommunityReports() {
  return request(
    "/api/v1/community-reports",
  );
}


export type CommunityReportInput = {
  location_id: string;

  report_type:
    | "SOIL_CRACK"
    | "ROCKFALL"
    | "WATER_SEEPAGE"
    | "GROUND_MOVEMENT"
    | "OTHER";

  description: string;

  severity:
    | "LOW"
    | "MODERATE"
    | "HIGH"
    | "CRITICAL";

  latitude?:
    | number
    | null;

  longitude?:
    | number
    | null;

  reporter_name?:
    | string
    | null;
};


export async function createCommunityReport(
  data: CommunityReportInput,
) {
  return request(
    "/api/v1/community-reports",
    {
      method:
        "POST",

      body:
        JSON.stringify(
          data,
        ),
    },
  );
}


export async function updateCommunityReportStatus(
  reportId: number,

  status:
    | "PENDING"
    | "VERIFIED"
    | "RESOLVED"
    | "REJECTED",
) {
  return request(
    `/api/v1/community-reports/${reportId}/status`,
    {
      method:
        "PATCH",

      body:
        JSON.stringify({
          status,
        }),
    },
  );
}


/* =========================================================
   GROUND VIBRATION + SENSOR FUSION
========================================================= */

export type VibrationReading = {
  id: number;
  location_id: string;
  sensor_id: string;
  sample_rate_hz: number;
  processing_status: string;
  vibration_risk_score: number;
  vibration_risk_level: string;
  movement_status: string;
  abnormal_ground_movement: boolean;
  contributing_factors: string[];
  recommended_actions: string[];
  assessment_mode: string;
  sample_count: number;
  window_duration_seconds: number;
  vibration_amplitude: number;
  rms_vibration: number;
  peak_acceleration: number;
  dominant_frequency_hz: number;
  signal_energy: number;
  tilt_change_deg: number;
  x_rms: number;
  y_rms: number;
  z_rms: number;
  captured_at: string;
  created_at: string;
};


export type VibrationThresholds = {
  acceleration_unit: string;
  rms_abnormal_mps2: number;
  peak_abnormal_mps2: number;
  tilt_abnormal_deg: number;
  assessment_mode: string;
  operational_warning: string;
};


export type VibrationWindowInput = {
  location_id: string;
  sensor_id: string;
  sample_rate_hz: number;
  x_samples: number[];
  y_samples: number[];
  z_samples: number[];
  tilt_change_deg?: number;
  captured_at?: string | null;
};


export type SensorFusionPredictionInput =
  VibrationWindowInput & {
    rainfall_mm_hr: number;
    soil_moisture_pct: number;
    tilt_deg: number;
    vegetation_change_pct: number;
    satellite_risk_index: number;
  };


export type SensorFusionPredictionResponse = {
  prediction_id: number;
  vibration_reading_id: number;
  alert_id: number | null;
  location_id: string;
  environmental_risk_score: number;
  environmental_risk_level: string;
  vibration_risk_score: number;
  vibration_risk_level: string;
  fused_risk_score: number;
  fused_risk_level: string;
  alert_generated: boolean;
  human_review_required: boolean;
  sensor_disagreement: boolean;
  cross_sensor_corroboration: boolean;
  fusion_method: string;
  model_used: string;
  contributing_factors: string[];
  recommended_actions: string[];
  analysis_message: string;
  vibration_analysis: VibrationReading;
};


export type VibrationReadingFilters = {
  locationId?: string;
  sensorId?: string;
  limit?: number;
};


export async function getVibrationReadings(
  filters: VibrationReadingFilters = {},
): Promise<VibrationReading[]> {
  const parameters = new URLSearchParams();

  if (filters.locationId) {
    parameters.set(
      "location_id",
      filters.locationId,
    );
  }

  if (filters.sensorId) {
    parameters.set(
      "sensor_id",
      filters.sensorId,
    );
  }

  parameters.set(
    "limit",
    String(filters.limit ?? 12),
  );

  return request<VibrationReading[]>(
    `/api/v1/vibration/readings?${parameters.toString()}`,
  );
}


export async function getVibrationThresholds():
Promise<VibrationThresholds> {
  return request<VibrationThresholds>(
    "/api/v1/vibration/thresholds",
  );
}


export async function analyzeVibration(
  data: VibrationWindowInput,
): Promise<VibrationReading> {
  return request<VibrationReading>(
    "/api/v1/vibration/analyze",
    {
      method: "POST",
      body: JSON.stringify(data),
    },
  );
}


export async function createSensorFusionPrediction(
  data: SensorFusionPredictionInput,
): Promise<SensorFusionPredictionResponse> {
  return request<SensorFusionPredictionResponse>(
    "/api/v1/vibration/fusion-predict",
    {
      method: "POST",
      body: JSON.stringify(data),
    },
  );
}
