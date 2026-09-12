import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getPredictions,
  getVibrationReadings,
  getVibrationThresholds,
  type PredictionRecord,
  type VibrationReading,
  type VibrationThresholds,
} from "../services/api";

import "./VibrationPanel.css";


const REFRESH_INTERVAL_MS = 30_000;


function clampPercent(value: number) {
  return Math.max(
    0,
    Math.min(100, value),
  );
}


function riskTone(level: string) {
  const normalized = level.toUpperCase();

  if (
    normalized === "HIGH" ||
    normalized === "CRITICAL"
  ) {
    return "danger";
  }

  if (
    normalized === "MODERATE" ||
    normalized === "MEDIUM"
  ) {
    return "warning";
  }

  return "safe";
}


function formatNumber(
  value: number,
  digits = 3,
) {
  return value.toLocaleString(
    undefined,
    {
      maximumFractionDigits: digits,
    },
  );
}


function formatTime(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Time unavailable";
  }

  return date.toLocaleString();
}


function getFusionWeights(
  prediction: PredictionRecord | undefined,
) {
  const match = prediction?.model_used.match(
    /fusion_v1:(\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)/i,
  );

  if (!match) {
    return {
      environmental: 75,
      vibration: 25,
      configured: false,
    };
  }

  return {
    environmental: Math.round(Number(match[1]) * 100),
    vibration: Math.round(Number(match[2]) * 100),
    configured: true,
  };
}


export default function VibrationPanel() {
  const [readings, setReadings] =
    useState<VibrationReading[]>([]);

  const [thresholds, setThresholds] =
    useState<VibrationThresholds | null>(null);

  const [predictions, setPredictions] =
    useState<PredictionRecord[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [lastSync, setLastSync] =
    useState<Date | null>(null);

  const loadVibrationData = useCallback(
    async () => {
      setLoading(true);

      const [
        readingsResult,
        thresholdsResult,
        predictionsResult,
      ] = await Promise.allSettled([
        getVibrationReadings({
          limit: 12,
        }),
        getVibrationThresholds(),
        getPredictions(),
      ]);

      if (readingsResult.status === "fulfilled") {
        setReadings(readingsResult.value);
        setError(null);
        setLastSync(new Date());
      } else {
        console.error(
          "Vibration readings error:",
          readingsResult.reason,
        );

        setError(
          "Ground-vibration data is temporarily unavailable.",
        );
      }

      if (thresholdsResult.status === "fulfilled") {
        setThresholds(thresholdsResult.value);
      }

      if (predictionsResult.status === "fulfilled") {
        setPredictions(predictionsResult.value);
      }

      setLoading(false);
    },
    [],
  );

  useEffect(() => {
    void loadVibrationData();

    const timer = window.setInterval(
      () => {
        void loadVibrationData();
      },
      REFRESH_INTERVAL_MS,
    );

    return () => window.clearInterval(timer);
  }, [loadVibrationData]);

  const latest = readings[0];

  const latestFusion = useMemo(
    () =>
      predictions.find((prediction) =>
        prediction.model_used
          .toLowerCase()
          .includes("fusion"),
      ),
    [predictions],
  );

  const trend = useMemo(
    () => [...readings].reverse(),
    [readings],
  );

  const fusionWeights = useMemo(
    () => getFusionWeights(latestFusion),
    [latestFusion],
  );

  const rmsProgress = latest && thresholds
    ? clampPercent(
        (latest.rms_vibration /
          thresholds.rms_abnormal_mps2) *
          100,
      )
    : 0;

  const peakProgress = latest && thresholds
    ? clampPercent(
        (latest.peak_acceleration /
          thresholds.peak_abnormal_mps2) *
          100,
      )
    : 0;

  const tiltProgress = latest && thresholds
    ? clampPercent(
        (Math.abs(latest.tilt_change_deg) /
          thresholds.tilt_abnormal_deg) *
          100,
      )
    : 0;

  const latestTone = latest
    ? riskTone(latest.vibration_risk_level)
    : "safe";

  return (
    <div className="vibration-panel">

      <div className="vibration-toolbar">
        <div className="vibration-connection">
          <span
            className={`vibration-connection-dot ${error ? "offline" : ""}`}
          />

          <div>
            <strong>
              {error
                ? "Sensor endpoint unavailable"
                : latest
                  ? "Sensor data online"
                  : "Awaiting sensor data"}
            </strong>

            <span>
              {lastSync
                ? `Synced ${lastSync.toLocaleTimeString()}`
                : "Connecting to the vibration network"}
            </span>
          </div>
        </div>

        <button
          type="button"
          onClick={() => void loadVibrationData()}
          disabled={loading}
        >
          {loading ? "Syncing…" : "↻ Refresh sensors"}
        </button>
      </div>

      {error && (
        <div className="vibration-inline-error">
          {error} Existing weather monitoring remains active.
        </div>
      )}

      {!latest && !loading ? (
        <article className="glass-card vibration-empty-state">
          <div className="vibration-empty-icon">
            ≋
          </div>

          <div>
            <span className="card-eyebrow">
              SENSOR NETWORK READY
            </span>

            <h3>
              No vibration windows stored yet
            </h3>

            <p>
              Submit one reading through POST /api/v1/vibration/analyze
              or run a fusion prediction. The dashboard will refresh
              automatically.
            </p>
          </div>
        </article>
      ) : latest ? (
        <>
          <div className="vibration-primary-grid">
            <article
              className={`glass-card vibration-risk-card ${latestTone}`}
            >
              <div className="vibration-risk-copy">
                <span className="card-eyebrow">
                  LATEST GROUND MOVEMENT
                </span>

                <div className="vibration-location-line">
                  <h3>
                    {latest.location_id}
                  </h3>

                  <span
                    className={`risk-pill ${latestTone}`}
                  >
                    {latest.vibration_risk_level}
                  </span>
                </div>

                <p>
                  Sensor {latest.sensor_id} · {formatTime(latest.captured_at)}
                </p>

                <div className="vibration-status-row">
                  <span>
                    <i />
                    {latest.movement_status}
                  </span>

                  <span>
                    {latest.sample_count} samples
                  </span>

                  <span>
                    {formatNumber(latest.sample_rate_hz, 0)} Hz sampling
                  </span>
                </div>
              </div>

              <div
                className="vibration-score-ring"
                style={{
                  background: `conic-gradient(var(--vibration-accent) ${clampPercent(latest.vibration_risk_score)}%, rgba(255,255,255,.07) 0)`,
                }}
              >
                <div>
                  <strong>
                    {Math.round(latest.vibration_risk_score)}
                  </strong>

                  <span>
                    / 100
                  </span>
                </div>
              </div>
            </article>

            <article className="glass-card fusion-summary-card">
              <div className="fusion-summary-heading">
                <div>
                  <span className="card-eyebrow">
                    MULTI-SENSOR DECISION
                  </span>

                  <h3>
                    Latest Fusion Risk
                  </h3>
                </div>

                {latestFusion && (
                  <span
                    className={`risk-pill ${riskTone(latestFusion.risk_level)}`}
                  >
                    {latestFusion.risk_level}
                  </span>
                )}
              </div>

              {latestFusion ? (
                <>
                  <div className="fusion-score-line">
                    <strong>
                      {Math.round(latestFusion.risk_score)}%
                    </strong>

                    <div>
                      <span>
                        {latestFusion.location_id}
                      </span>

                      <small>
                        {formatTime(latestFusion.predicted_at)}
                      </small>
                    </div>
                  </div>

                  <div className="fusion-weight-track">
                    <span
                      style={{
                        width: `${fusionWeights.environmental}%`,
                      }}
                    />

                    <i
                      style={{
                        width: `${fusionWeights.vibration}%`,
                      }}
                    />
                  </div>

                  <p>
                    {fusionWeights.configured
                      ? `${fusionWeights.environmental}% environmental · ${fusionWeights.vibration}% vibration`
                      : "Explainable weighted sensor fusion"}
                  </p>

                  <div
                    className={`fusion-alert-state ${latestFusion.alert_generated ? "active" : ""}`}
                  >
                    <span>
                      {latestFusion.alert_generated ? "⚠" : "✓"}
                    </span>

                    <div>
                      <strong>
                        {latestFusion.alert_generated
                          ? "Early warning generated"
                          : "No fusion alert required"}
                      </strong>

                      <small>
                        Stored prediction #{latestFusion.id}
                      </small>
                    </div>
                  </div>
                </>
              ) : (
                <div className="fusion-empty">
                  <strong>
                    Fusion engine is ready
                  </strong>

                  <p>
                    Run POST /api/v1/vibration/fusion-predict to create
                    the first combined environmental and vibration result.
                  </p>
                </div>
              )}
            </article>
          </div>

          <div className="vibration-metric-grid">
            <SensorMetric
              label="RMS vibration"
              value={formatNumber(latest.rms_vibration)}
              unit="m/s²"
              note={
                thresholds
                  ? `Threshold ${formatNumber(thresholds.rms_abnormal_mps2)}`
                  : "Processed signal strength"
              }
              progress={rmsProgress}
              tone={latestTone}
            />

            <SensorMetric
              label="Peak acceleration"
              value={formatNumber(latest.peak_acceleration)}
              unit="m/s²"
              note={
                thresholds
                  ? `Threshold ${formatNumber(thresholds.peak_abnormal_mps2)}`
                  : "Highest filtered acceleration"
              }
              progress={peakProgress}
              tone={latestTone}
            />

            <SensorMetric
              label="Dominant frequency"
              value={formatNumber(latest.dominant_frequency_hz, 2)}
              unit="Hz"
              note="Strongest vibration frequency"
              progress={clampPercent(latest.dominant_frequency_hz * 2)}
              tone="frequency"
            />

            <SensorMetric
              label="Tilt change"
              value={formatNumber(latest.tilt_change_deg, 2)}
              unit="deg"
              note={
                thresholds
                  ? `Threshold ±${formatNumber(thresholds.tilt_abnormal_deg, 2)}`
                  : "Window-level movement"
              }
              progress={tiltProgress}
              tone={latestTone}
            />
          </div>

          <div className="vibration-detail-grid">
            <article className="glass-card vibration-trend-card">
              <div className="vibration-card-heading">
                <div>
                  <span className="card-eyebrow">
                    RECENT SENSOR WINDOWS
                  </span>

                  <h3>
                    Vibration Risk Trend
                  </h3>
                </div>

                <span>
                  Latest {trend.length}
                </span>
              </div>

              <div
                className="vibration-chart"
                role="img"
                aria-label="Recent vibration risk scores from oldest to newest"
              >
                <div className="vibration-chart-grid">
                  <span>100</span>
                  <span>75</span>
                  <span>50</span>
                  <span>25</span>
                </div>

                <div className="vibration-bars">
                  {trend.map((reading) => (
                    <div
                      className="vibration-bar-column"
                      key={reading.id}
                    >
                      <div
                        className={`vibration-bar ${riskTone(reading.vibration_risk_level)}`}
                        style={{
                          height: `${Math.max(5, clampPercent(reading.vibration_risk_score))}%`,
                        }}
                        title={`${reading.location_id}: ${reading.vibration_risk_score}%`}
                      />

                      <span>
                        {reading.vibration_risk_score.toFixed(0)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="vibration-axis-grid">
                <AxisStrength
                  axis="X"
                  value={latest.x_rms}
                  maximum={Math.max(
                    latest.x_rms,
                    latest.y_rms,
                    latest.z_rms,
                    0.001,
                  )}
                />

                <AxisStrength
                  axis="Y"
                  value={latest.y_rms}
                  maximum={Math.max(
                    latest.x_rms,
                    latest.y_rms,
                    latest.z_rms,
                    0.001,
                  )}
                />

                <AxisStrength
                  axis="Z"
                  value={latest.z_rms}
                  maximum={Math.max(
                    latest.x_rms,
                    latest.y_rms,
                    latest.z_rms,
                    0.001,
                  )}
                />
              </div>
            </article>

            <article className="glass-card vibration-insight-card">
              <span className="card-eyebrow">
                EXPLAINABLE AI
              </span>

              <h3>
                Why this status?
              </h3>

              <div className="vibration-insight-block">
                <strong>
                  Contributing factors
                </strong>

                <ul>
                  {latest.contributing_factors.map((factor) => (
                    <li key={factor}>
                      {factor}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="vibration-insight-block actions">
                <strong>
                  Recommended actions
                </strong>

                <ul>
                  {latest.recommended_actions.map((action) => (
                    <li key={action}>
                      {action}
                    </li>
                  ))}
                </ul>
              </div>
            </article>
          </div>

          {thresholds && (
            <div className="vibration-calibration-note">
              <span>
                CALIBRATION STATUS
              </span>

              <p>
                {thresholds.operational_warning}
              </p>

              <small>
                Mode: {thresholds.assessment_mode.replaceAll("_", " ")}
              </small>
            </div>
          )}
        </>
      ) : (
        <div className="glass-card vibration-loading-state">
          Loading ground-vibration intelligence…
        </div>
      )}
    </div>
  );
}


function SensorMetric({
  label,
  value,
  unit,
  note,
  progress,
  tone,
}: {
  label: string;
  value: string;
  unit: string;
  note: string;
  progress: number;
  tone: string;
}) {
  return (
    <article className="glass-card vibration-metric-card">
      <span>
        {label}
      </span>

      <div>
        <strong>
          {value}
        </strong>

        <small>
          {unit}
        </small>
      </div>

      <p>
        {note}
      </p>

      <div className="vibration-metric-track">
        <i
          className={tone}
          style={{
            width: `${progress}%`,
          }}
        />
      </div>
    </article>
  );
}


function AxisStrength({
  axis,
  value,
  maximum,
}: {
  axis: string;
  value: number;
  maximum: number;
}) {
  const percent = clampPercent(
    (value / maximum) * 100,
  );

  return (
    <div className="vibration-axis-row">
      <span>
        {axis}
      </span>

      <div>
        <i
          style={{
            width: `${percent}%`,
          }}
        />
      </div>

      <strong>
        {formatNumber(value)}
      </strong>
    </div>
  );
}
