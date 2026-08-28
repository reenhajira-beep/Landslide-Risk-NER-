import {
  useEffect,
  useMemo,
  useState,
} from "react";

import MapView from "../components/MapView";

import {
  getLatestLiveMonitoring,
  type LiveMonitoringData,
} from "../services/api";

type Section =
  | "home"
  | "overview"
  | "map"
  | "alerts"
  | "locations";

export default function Dashboard() {
  const [locations, setLocations] =
    useState<LiveMonitoringData[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [activeSection, setActiveSection] =
    useState<Section>("home");

  const [lastUpdated, setLastUpdated] =
    useState<Date | null>(null);

  async function loadDashboard() {
    try {
      setError(null);

      const data =
        await getLatestLiveMonitoring();

      setLocations(
        Array.isArray(data)
          ? data
          : [],
      );

      setLastUpdated(new Date());
    } catch (err) {
      console.error(
        "Dashboard load error:",
        err,
      );

      setError(
        "Unable to connect to SENTINEL live monitoring.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();

    const timer =
      window.setInterval(
        () => {
          void loadDashboard();
        },
        30000,
      );

    return () =>
      window.clearInterval(timer);
  }, []);

  const summary = useMemo(() => {
    const high =
      locations.filter((item) =>
        [
          "HIGH",
          "CRITICAL",
        ].includes(
          item.risk_level.toUpperCase(),
        ),
      );

    const moderate =
      locations.filter((item) =>
        [
          "MODERATE",
          "MEDIUM",
        ].includes(
          item.risk_level.toUpperCase(),
        ),
      );

    const low =
      locations.filter(
        (item) =>
          item.risk_level.toUpperCase() ===
          "LOW",
      );

    const highestRisk =
      [...locations].sort(
        (a, b) =>
          b.risk_score -
          a.risk_score,
      )[0];

    const rainiest =
      [...locations].sort(
        (a, b) =>
          b.rainfall_mm_hr -
          a.rainfall_mm_hr,
      )[0];

    return {
      high,
      moderate,
      low,
      highestRisk,
      rainiest,
    };
  }, [locations]);

  function scrollToSection(
    section: Section,
  ) {
    setActiveSection(section);

    const element =
      document.getElementById(
        section,
      );

    element?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  return (
    <div className="sentinel-galaxy-app">

      {/* =====================================================
          HERO
      ===================================================== */}

      <section
        id="home"
        className="galaxy-hero"
      >
        <div className="hero-dark-overlay" />

        <div className="moving-stars stars-one" />
        <div className="moving-stars stars-two" />

        {/* NAVBAR */}

        <header className="top-navbar">

          <button
            type="button"
            className="top-brand"
            onClick={() =>
              scrollToSection("home")
            }
          >
            <div className="brand-orbit">
              S
            </div>

            <div>
              <strong>
                SENTINEL-NER
              </strong>

              <span>
                Disaster Intelligence
              </span>
            </div>
          </button>


          <nav className="desktop-nav">

            <button
              className={
                activeSection === "home"
                  ? "active"
                  : ""
              }
              onClick={() =>
                scrollToSection("home")
              }
            >
              Home
            </button>

            <button
              className={
                activeSection === "overview"
                  ? "active"
                  : ""
              }
              onClick={() =>
                scrollToSection(
                  "overview",
                )
              }
            >
              Overview
            </button>

            <button
              className={
                activeSection === "map"
                  ? "active"
                  : ""
              }
              onClick={() =>
                scrollToSection("map")
              }
            >
              Live Map
            </button>

            <button
              className={
                activeSection === "alerts"
                  ? "active"
                  : ""
              }
              onClick={() =>
                scrollToSection(
                  "alerts",
                )
              }
            >
              Alerts

              {summary.high.length >
                0 && (
                <span className="nav-alert-count">
                  {summary.high.length}
                </span>
              )}
            </button>

            <button
              className={
                activeSection === "locations"
                  ? "active"
                  : ""
              }
              onClick={() =>
                scrollToSection(
                  "locations",
                )
              }
            >
              Locations
            </button>

          </nav>


          <button
            type="button"
            className="nav-cta"
            onClick={() =>
              scrollToSection("map")
            }
          >
            Live System
          </button>

        </header>


        {/* HERO CONTENT */}

        <div className="hero-content">

          <span className="hero-eyebrow">
            AI POWERED LANDSLIDE
            EARLY WARNING SYSTEM
          </span>

          <h1>
            SENTINEL
          </h1>

          <div className="energy-line">
            <span />
          </div>

          <h2>
            Predict risk before
            disaster strikes.
          </h2>

          <p>
            Real-time weather monitoring,
            GIS intelligence, satellite
            indicators and AI-powered
            landslide risk analysis for
            vulnerable regions.
          </p>


          <div className="hero-buttons">

            <button
              className="hero-primary-button"
              onClick={() =>
                scrollToSection(
                  "overview",
                )
              }
            >
              Explore Monitoring
            </button>

            <button
              className="hero-secondary-button"
              onClick={() =>
                void loadDashboard()
              }
            >
              ↻ Refresh Data
            </button>

          </div>

        </div>


        {/* LIVE STATUS */}

        <div className="hero-live-status">

          <span className="live-indicator" />

          <strong>
            LIVE
          </strong>

          <span>
            {locations.length}
            {" "}
            monitored locations
          </span>

          <span>
            {lastUpdated
              ? lastUpdated.toLocaleTimeString()
              : "Connecting..."}
          </span>

        </div>


        <button
          className="scroll-down"
          onClick={() =>
            scrollToSection(
              "overview",
            )
          }
        >
          ↓
        </button>

      </section>


      {/* =====================================================
          DASHBOARD AREA
      ===================================================== */}

      <main className="dashboard-world">

        {error && (
          <div className="global-error">
            {error}
          </div>
        )}


        {/* =================================================
            OVERVIEW
        ================================================= */}

        <section
          id="overview"
          className="dashboard-section"
        >

          <SectionHeader
            eyebrow="SENTINEL INTELLIGENCE"
            title="Live Risk Overview"
            description="Latest environmental and AI risk analysis from the monitoring network."
            buttonText="Refresh"
            onButtonClick={() =>
              void loadDashboard()
            }
          />


          <div className="overview-grid">

            {/* MAIN WEATHER + RISK */}

            <article className="glass-card main-overview-card">

              <div className="overview-top">

                <div>

                  <span className="card-eyebrow">
                    HIGHEST RISK LOCATION
                  </span>

                  <h3>
                    {summary.highestRisk
                      ?.location_name ??
                      "Waiting for data"}
                  </h3>

                  <p>
                    {summary.highestRisk
                      ?.state ??
                      "Monitoring network"}
                  </p>

                </div>


                <RiskGauge
                  score={
                    summary.highestRisk
                      ?.risk_score ??
                    0
                  }
                />

              </div>


              {summary.highestRisk && (

                <div className="environment-grid">

                  <ValueTile
                    icon="🌡"
                    label="Temperature"
                    value={`${summary.highestRisk.temperature_c}°C`}
                  />

                  <ValueTile
                    icon="💧"
                    label="Humidity"
                    value={`${summary.highestRisk.relative_humidity_pct}%`}
                  />

                  <ValueTile
                    icon="🌧"
                    label="Rainfall"
                    value={`${summary.highestRisk.rainfall_mm_hr} mm/hr`}
                  />

                  <ValueTile
                    icon="💨"
                    label="Wind"
                    value={`${summary.highestRisk.wind_speed_kmh} km/h`}
                  />

                  <ValueTile
                    icon="◉"
                    label="Soil Moisture"
                    value={`${summary.highestRisk.soil_moisture_pct}%`}
                  />

                  <ValueTile
                    icon="◈"
                    label="Satellite Risk"
                    value={`${summary.highestRisk.satellite_risk_index}`}
                  />

                </div>

              )}

            </article>


            {/* COUNTERS */}

            <div className="overview-counter-grid">

              <CounterCard
                label="High Risk"
                value={summary.high.length}
                type="high"
              />

              <CounterCard
                label="Moderate"
                value={
                  summary.moderate.length
                }
                type="moderate"
              />

              <CounterCard
                label="Low Risk"
                value={summary.low.length}
                type="low"
              />

              <CounterCard
                label="Locations"
                value={locations.length}
                type="total"
              />

            </div>

          </div>


          {/* WEATHER FEATURE */}

          {summary.rainiest && (

            <article className="rain-feature glass-card">

              <div>

                <span className="card-eyebrow">
                  LIVE WEATHER SIGNAL
                </span>

                <h3>
                  Heaviest Rainfall
                </h3>

                <strong>
                  {summary.rainiest.location_name}
                </strong>

                <p>
                  {summary.rainiest.state}
                </p>

              </div>


              <div className="rain-feature-value">

                <span>
                  🌧
                </span>

                <strong>
                  {
                    summary.rainiest
                      .rainfall_mm_hr
                  }
                </strong>

                <small>
                  mm/hr
                </small>

              </div>

            </article>

          )}

        </section>


        {/* =================================================
            LIVE MAP
        ================================================= */}

        <section
          id="map"
          className="dashboard-section"
        >

          <SectionHeader
            eyebrow="LIVE GIS NETWORK"
            title="India Landslide Risk Map"
            description="Interactive monitoring map showing the latest risk condition for every location."
          />


          <div className="map-legend">

            <Legend
              color="#40df9b"
              text="Low"
            />

            <Legend
              color="#ffb64d"
              text="Moderate"
            />

            <Legend
              color="#ff4962"
              text="High"
            />

          </div>


          <article className="glass-card map-card">
            <MapView />
          </article>

        </section>


        {/* =================================================
            ALERTS
        ================================================= */}

        <section
          id="alerts"
          className="dashboard-section"
        >

          <SectionHeader
            eyebrow="EARLY WARNING NETWORK"
            title="Active Landslide Alerts"
            description="High-risk locations detected by the SENTINEL analysis agent."
          />


          <div className="alerts-title-row">

            <span
              className={
                summary.high.length > 0
                  ? "active-alert-badge danger"
                  : "active-alert-badge"
              }
            >
              <i />
              {summary.high.length}
              {" "}
              Active
            </span>

          </div>


          {summary.high.length ===
          0 ? (

            <div className="glass-card all-safe-card">

              <div className="safe-check">
                ✓
              </div>

              <div>

                <strong>
                  No high-risk alerts
                </strong>

                <p>
                  Current monitored
                  locations are below the
                  high-risk threshold.
                </p>

              </div>

            </div>

          ) : (

            <div className="alerts-grid">

              {summary.high.map(
                (location) => (

                  <AlertCard
                    key={
                      location.location_id
                    }
                    location={
                      location
                    }
                  />

                ),
              )}

            </div>

          )}

        </section>


        {/* =================================================
            LOCATIONS
        ================================================= */}

        <section
          id="locations"
          className="dashboard-section"
        >

          <SectionHeader
            eyebrow="MONITORING NETWORK"
            title="Live Locations"
            description="Environmental and landslide-risk information for all monitored regions."
          />


          {loading ? (

            <div className="loading-card">
              Loading monitoring
              network...
            </div>

          ) : (

            <div className="locations-grid">

              {locations.map(
                (location) => (

                  <LocationCard
                    key={
                      location.location_id
                    }
                    location={
                      location
                    }
                  />

                ),
              )}

            </div>

          )}

        </section>

      </main>

    </div>
  );
}


/* =========================================================
   SECTION HEADER
========================================================= */

function SectionHeader({
  eyebrow,
  title,
  description,
  buttonText,
  onButtonClick,
}: {
  eyebrow: string;
  title: string;
  description: string;
  buttonText?: string;
  onButtonClick?: () => void;
}) {
  return (
    <div className="section-header">

      <div>

        <span>
          {eyebrow}
        </span>

        <h2>
          {title}
        </h2>

        <p>
          {description}
        </p>

      </div>


      {buttonText &&
        onButtonClick && (

        <button
          onClick={
            onButtonClick
          }
        >
          ↻ {buttonText}
        </button>

      )}

    </div>
  );
}


/* =========================================================
   RISK GAUGE
========================================================= */

function RiskGauge({
  score,
}: {
  score: number;
}) {
  const safeScore =
    Math.max(
      0,
      Math.min(
        100,
        score,
      ),
    );

  return (
    <div
      className="risk-gauge"
      style={{
        background: `
          conic-gradient(
            #65d7ff 0%,
            #7b79ff ${safeScore * 0.55}%,
            #e56cff ${safeScore}%,
            rgba(255,255,255,.08)
            ${safeScore}% 100%
          )
        `,
      }}
    >

      <div className="risk-gauge-core">

        <strong>
          {Math.round(
            safeScore,
          )}
          %
        </strong>

        <span>
          {safeScore >= 70
            ? "HIGH"
            : safeScore >= 40
              ? "MODERATE"
              : "LOW"}
        </span>

      </div>

    </div>
  );
}


/* =========================================================
   VALUE TILE
========================================================= */

function ValueTile({
  icon,
  label,
  value,
}: {
  icon: string;
  label: string;
  value: string;
}) {
  return (
    <div className="value-tile">

      <span className="value-icon">
        {icon}
      </span>

      <div>

        <small>
          {label}
        </small>

        <strong>
          {value}
        </strong>

      </div>

    </div>
  );
}


/* =========================================================
   COUNTER
========================================================= */

function CounterCard({
  label,
  value,
  type,
}: {
  label: string;
  value: number;
  type:
    | "high"
    | "moderate"
    | "low"
    | "total";
}) {
  return (
    <div
      className={`counter-card ${type}`}
    >

      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

      <div className="counter-graph">
        <i />
        <i />
        <i />
        <i />
        <i />
      </div>

    </div>
  );
}


/* =========================================================
   LEGEND
========================================================= */

function Legend({
  color,
  text,
}: {
  color: string;
  text: string;
}) {
  return (
    <span className="legend">

      <i
        style={{
          background: color,
        }}
      />

      {text}

    </span>
  );
}


/* =========================================================
   ALERT CARD
========================================================= */

function AlertCard({
  location,
}: {
  location:
    LiveMonitoringData;
}) {
  return (
    <article className="alert-card">

      <div className="alert-radar">

        <span className="radar-wave wave-one" />
        <span className="radar-wave wave-two" />
        <span className="radar-wave wave-three" />

        <div className="radar-core">
          ⚠
        </div>

      </div>


      <div className="alert-card-content">

        <span className="danger-label">
          HIGH RISK DETECTED
        </span>

        <h3>
          {location.location_name}
        </h3>

        <p>
          {location.state}
        </p>


        <div className="alert-value-grid">

          <MiniValue
            label="Risk"
            value={`${Math.round(
              location.risk_score,
            )}%`}
          />

          <MiniValue
            label="Rain"
            value={`${location.rainfall_mm_hr}`}
          />

          <MiniValue
            label="Humidity"
            value={`${location.relative_humidity_pct}%`}
          />

          <MiniValue
            label="Soil"
            value={`${location.soil_moisture_pct}%`}
          />

        </div>

      </div>

    </article>
  );
}


/* =========================================================
   MINI VALUE
========================================================= */

function MiniValue({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="mini-value">

      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

    </div>
  );
}


/* =========================================================
   LOCATION CARD
========================================================= */

function LocationCard({
  location,
}: {
  location:
    LiveMonitoringData;
}) {
  const risk =
    location.risk_level
      .toUpperCase();

  const riskClass =
    risk === "HIGH" ||
    risk === "CRITICAL"
      ? "danger"
      : risk === "MODERATE" ||
          risk === "MEDIUM"
        ? "warning"
        : "safe";

  return (
    <article className="location-card">

      <div className="location-card-header">

        <div>

          <h3>
            {location.location_name}
          </h3>

          <span>
            {location.state}
          </span>

        </div>


        <span
          className={`risk-pill ${riskClass}`}
        >
          {location.risk_level}
        </span>

      </div>


      <div className="location-data">

        <MiniValue
          label="Temp"
          value={`${location.temperature_c}°C`}
        />

        <MiniValue
          label="Rain"
          value={`${location.rainfall_mm_hr}`}
        />

        <MiniValue
          label="Humidity"
          value={`${location.relative_humidity_pct}%`}
        />

        <MiniValue
          label="Risk"
          value={`${location.risk_score}`}
        />

      </div>

    </article>
  );
}