import { ArrowRight } from "lucide-react";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import { Link } from "react-router-dom";
import "leaflet/dist/leaflet.css";
import type { StationSummary } from "../api/types";
import { ETAT_COLORS, ETAT_LABELS } from "../constants/etat";
import { useTheme } from "../hooks/useTheme";

const PARIS_CENTER: [number, number] = [48.8566, 2.3522];

// Tuiles OpenStreetMap standard (gratuites, sans clé). Le mode sombre
// s'obtient en filtrant le calque de tuiles en CSS (.leaflet-tile-pane,
// voir index.css) plutôt que via un second fournisseur de tuiles "dark" :
// les quelques services gratuits de ce type (CARTO notamment) exigent
// désormais une clé API, ce qu'on veut éviter pour rester cohérent avec
// le reste du projet (open data, sans clé).
const OSM_TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export function StationMap({ stations }: { stations: StationSummary[] }) {
  const theme = useTheme();

  return (
    <MapContainer
      center={PARIS_CENTER}
      zoom={12}
      preferCanvas
      style={{ height: "100%", width: "100%", borderRadius: "var(--radius-lg)" }}
    >
      <TileLayer attribution={OSM_ATTRIBUTION} url={OSM_TILE_URL} />
      {stations.map((station) => {
        const color = ETAT_COLORS[station.etat];
        return (
          <CircleMarker
            key={station.station_id}
            center={[station.lat, station.lon]}
            radius={6.5}
            pathOptions={{
              color: theme === "dark" ? "#091414" : "#ffffff",
              fillColor: color,
              fillOpacity: 0.92,
              weight: 1.25,
            }}
          >
            <Popup minWidth={180}>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <strong style={{ fontSize: "0.95rem" }}>{station.name}</strong>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: "0.82rem",
                    fontWeight: 600,
                    color,
                  }}
                >
                  <span
                    aria-hidden="true"
                    style={{ width: 8, height: 8, borderRadius: "50%", background: color }}
                  />
                  {ETAT_LABELS[station.etat]}
                </span>
                {station.num_mechanical !== null && station.num_ebike !== null && (
                  <span style={{ fontSize: "0.82rem", color: "#4c5f5d" }}>
                    {station.num_mechanical} mécaniques · {station.num_ebike} électriques
                  </span>
                )}
                <Link
                  to={`/stations/${station.station_id}`}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                    fontSize: "0.82rem",
                    fontWeight: 650,
                    marginTop: 2,
                  }}
                >
                  Voir la fiche station <ArrowRight size={13} />
                </Link>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
