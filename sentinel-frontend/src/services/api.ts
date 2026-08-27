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

export async function getPredictions() {
  return request(
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