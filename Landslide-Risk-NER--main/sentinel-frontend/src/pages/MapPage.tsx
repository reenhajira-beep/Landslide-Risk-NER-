import MapView from "../components/MapView";

export default function MapPage() {
  return (
    <div
      style={{
        padding: "24px",
      }}
    >
      <h1
        style={{
          marginBottom: "8px",
        }}
      >
        North-East India Risk Map
      </h1>

      <p
        style={{
          color: "#9bb4a8",
          marginBottom: "20px",
        }}
      >
        Monitor landslide-prone areas using GIS,
        satellite imagery and prediction data.
      </p>

      <MapView />
    </div>
  );
}