import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import { Link } from "react-router-dom";
import "leaflet/dist/leaflet.css";
import type { StationSummary } from "../api/types";
import { ETAT_COLORS, ETAT_LABELS } from "../constants/etat";

const PARIS_CENTER: [number, number] = [48.8566, 2.3522];

export function StationMap({ stations }: { stations: StationSummary[] }) {
  return (
    <MapContainer
      center={PARIS_CENTER}
      zoom={12}
      preferCanvas
      style={{ height: "100%", width: "100%", borderRadius: "var(--radius)" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {stations.map((station) => (
        <CircleMarker
          key={station.station_id}
          center={[station.lat, station.lon]}
          radius={6}
          pathOptions={{
            color: ETAT_COLORS[station.etat],
            fillColor: ETAT_COLORS[station.etat],
            fillOpacity: 0.85,
            weight: 1,
          }}
        >
          <Popup>
            <strong>{station.name}</strong>
            <br />
            {ETAT_LABELS[station.etat]}
            {station.num_mechanical !== null && station.num_ebike !== null && (
              <>
                <br />
                {station.num_mechanical} mécaniques · {station.num_ebike} électriques
              </>
            )}
            <br />
            <Link to={`/stations/${station.station_id}`}>Voir la fiche station</Link>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
