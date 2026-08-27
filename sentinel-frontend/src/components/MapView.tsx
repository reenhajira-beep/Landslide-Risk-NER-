import { Fragment, useEffect, useState } from "react";
import {
  CircleMarker,
  LayersControl,
  MapContainer,
  Popup,
  TileLayer,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

import {
  getLatestLiveMonitoring,
  type LiveMonitoringData,
} from "../services/api";

const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

function getRiskColor(riskLevel: string): string {
  const risk = riskLevel.trim().toUpperCase();

  if (risk === "HIGH" || risk === "CRITICAL") {
    return "#ff4962";
  }

  if (risk === "MODERATE" || risk === "MEDIUM") {
    return "#ffb64d";
  }

  return "#40df9b";
}

function getMarkerRadius(riskLevel: string): number {
  const risk = riskLevel.trim().toUpperCase();

  if (risk === "HIGH" || risk === "CRITICAL") {
    return 10;
  }

  if (risk === "MODERATE" || risk === "MEDIUM") {
    return 8;
  }

  return 6;
}

function isHighRisk(riskLevel: string): boolean {
  const risk = riskLevel.trim().toUpperCase();
  return risk === "HIGH" || risk === "CRITICAL";
}

export default function MapView() {
  const [locations, setLocations] = useState<LiveMonitoringData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadLocations() {
    try {
      setError(null);

      const data = await getLatestLiveMonitoring();

      setLocations(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Map data error:", err);
      setError("Unable to load live map data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadLocations();

    const timer = window.setInterval(() => {
      void loadLocations();
    }, REFRESH_INTERVAL_MS);

    return () => {
      window.clearInterval(timer);
    };
  }, []);

  if (loading) {
    return (
      <div className="map-loading">
        Loading live risk map...
      </div>
    );
  }

  if (error) {
    return (
      <div className="map-loading">
        {error}
      </div>
    );
  }

  return (
    <div className="map-wrapper">
      <MapContainer
        center={[20.5937, 78.9629]}
        zoom={5}
        minZoom={4}
        maxZoom={16}
        scrollWheelZoom
        style={{
          width: "100%",
          height: "100%",
        }}
      >
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked name="Street Map">
            <TileLayer
              attribution="© OpenStreetMap contributors"
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
          </LayersControl.BaseLayer>

          <LayersControl.BaseLayer name="Satellite">
            <TileLayer
              attribution="Tiles © Esri"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
          </LayersControl.BaseLayer>
        </LayersControl>

        {locations.map((location) => {
          const color = getRiskColor(location.risk_level);

          return (
            <Fragment key={location.location_id}>
              {isHighRisk(location.risk_level) && (
                <CircleMarker
                  center={[location.latitude, location.longitude]}
                  radius={19}
                  pathOptions={{
                    color,
                    fillColor: color,
                    fillOpacity: 0.10,
                    opacity: 0.55,
                    weight: 2,
                  }}
                />
              )}

              <CircleMarker
                center={[location.latitude, location.longitude]}
                radius={getMarkerRadius(location.risk_level)}
                pathOptions={{
                  color,
                  fillColor: color,
                  fillOpacity: 0.95,
                  weight: 3,
                }}
              >
                <Popup>
                  <div className="sentinel-popup">
                    <h3>{location.location_name}</h3>
                    <p>{location.state}</p>

                    <div>
                      Risk:{" "}
                      <strong style={{ color }}>
                        {location.risk_level}
                      </strong>
                    </div>

                    <div>Score: {location.risk_score}</div>
                    <div>Temperature: {location.temperature_c}°C</div>
                    <div>Rainfall: {location.rainfall_mm_hr} mm/hr</div>
                    <div>Humidity: {location.relative_humidity_pct}%</div>
                    <div>Wind: {location.wind_speed_kmh} km/h</div>
                    <div>Soil moisture: {location.soil_moisture_pct}%</div>
                  </div>
                </Popup>
              </CircleMarker>
            </Fragment>
          );
        })}
      </MapContainer>
    </div>
  );
}
