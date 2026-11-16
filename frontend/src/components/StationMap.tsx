import L from "leaflet";
import { LocateFixed } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";
import { Link } from "react-router-dom";
import "leaflet/dist/leaflet.css";
import { fetchStationPrediction } from "../api/client";
import type { StationPrediction, StationSummary } from "../api/types";
import { ETAT_COLORS, ETAT_LABELS } from "../constants/etat";
import { useTheme } from "../hooks/useTheme";
import { formatNumber, shortCommune } from "../lib/format";
import { toBikeCount } from "./PredictionPanel";

const PARIS_CENTER: [number, number] = [48.8566, 2.3522];

// Marqueurs individuels à partir de ce zoom ; en dessous, stations regroupées.
const INDIVIDUAL_ZOOM = 14;
const CLUSTER_CELL_PX = 64;

// Tuiles OpenStreetMap (gratuites, sans clé). CARTO Positron / Dark Matter
// exigent désormais une clé API (filigrane « API KEY REQUIRED », constaté) :
// le rendu sobre vient donc d'un filtre CSS (voir index.css, .leaflet-tile-pane).
const TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

// Cache des prévisions déjà demandées au survol : évite de réinterroger
// l'API quand on repasse sur la même station.
const predictionCache = new Map<number, StationPrediction | null>();

interface Cluster {
  key: string;
  lat: number;
  lon: number;
  members: StationSummary[];
}

function buildClusters(map: L.Map, stations: StationSummary[], zoom: number): Cluster[] {
  const cells = new Map<string, Cluster>();
  for (const station of stations) {
    const p = map.project([station.lat, station.lon], zoom);
    const key = `${Math.floor(p.x / CLUSTER_CELL_PX)}:${Math.floor(p.y / CLUSTER_CELL_PX)}`;
    const cluster = cells.get(key);
    if (cluster) cluster.members.push(station);
    else cells.set(key, { key, lat: 0, lon: 0, members: [station] });
  }
  for (const cluster of cells.values()) {
    cluster.lat = cluster.members.reduce((s, m) => s + m.lat, 0) / cluster.members.length;
    cluster.lon = cluster.members.reduce((s, m) => s + m.lon, 0) / cluster.members.length;
  }
  return [...cells.values()];
}

function clusterIcon(count: number): L.DivIcon {
  const size = count < 10 ? 32 : count < 50 ? 38 : 46;
  return L.divIcon({
    html: `<div class="map-cluster" style="width:${size}px;height:${size}px">${formatNumber(count)}</div>`,
    className: "map-cluster-wrap",
    iconSize: [size, size],
  });
}

function StationPopup({ station, active }: { station: StationSummary; active: boolean }) {
  const [prediction, setPrediction] = useState<StationPrediction | null | undefined>(
    predictionCache.get(station.station_id),
  );

  useEffect(() => {
    if (!active || predictionCache.has(station.station_id)) return;
    let cancelled = false;
    fetchStationPrediction(station.station_id)
      .then((p) => predictionCache.set(station.station_id, p))
      .catch(() => predictionCache.set(station.station_id, null))
      .finally(() => {
        if (!cancelled) setPrediction(predictionCache.get(station.station_id));
      });
    // On oublie la valeur après 60 s : la prévision suit le flux en direct.
    const timer = setTimeout(() => predictionCache.delete(station.station_id), 60_000);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [active, station.station_id]);

  const color = ETAT_COLORS[station.etat];
  return (
    <div className="map-popup">
      <strong className="map-popup-name">{station.name}</strong>
      <span className="map-popup-etat" style={{ color }}>
        <span aria-hidden="true" className="chip-dot" style={{ background: color }} />
        {ETAT_LABELS[station.etat]} · {shortCommune(station.commune_nom)}
      </span>
      <dl className="map-popup-grid">
        <dt>Vélos mécaniques</dt>
        <dd>{station.num_mechanical ?? "—"}</dd>
        <dt>Vélos électriques</dt>
        <dd>{station.num_ebike ?? "—"}</dd>
        <dt>Bornes libres</dt>
        <dd>{station.num_docks_available ?? "—"}</dd>
        <dt>Dans 30 min</dt>
        <dd>
          {prediction === undefined
            ? "…"
            : prediction === null
              ? "indisponible"
              : `${toBikeCount(prediction.prediction_30min, station.capacity)} vélos`}
        </dd>
      </dl>
      <Link to={`/stations/${station.station_id}`} className="map-popup-link">
        Voir la station
      </Link>
    </div>
  );
}

function Markers({ stations }: { stations: StationSummary[] }) {
  const map = useMap();
  const theme = useTheme();
  const [zoom, setZoom] = useState(map.getZoom());
  const [bounds, setBounds] = useState(() => map.getBounds());
  const [openId, setOpenId] = useState<number | null>(null);

  useMapEvents({
    zoomend: () => setZoom(map.getZoom()),
    moveend: () => setBounds(map.getBounds()),
  });

  const clusters = useMemo(
    () => (zoom < INDIVIDUAL_ZOOM ? buildClusters(map, stations, zoom) : []),
    [map, stations, zoom],
  );

  if (zoom < INDIVIDUAL_ZOOM) {
    return (
      <>
        {clusters.map((cluster) =>
          cluster.members.length === 1 ? (
            <StationMarker
              key={cluster.key}
              station={cluster.members[0]}
              theme={theme}
              openId={openId}
              setOpenId={setOpenId}
            />
          ) : (
            <Marker
              key={cluster.key}
              position={[cluster.lat, cluster.lon]}
              icon={clusterIcon(cluster.members.length)}
              eventHandlers={{
                click: () =>
                  map.fitBounds(L.latLngBounds(cluster.members.map((m) => [m.lat, m.lon] as [number, number])), {
                    padding: [48, 48],
                    maxZoom: INDIVIDUAL_ZOOM + 1,
                  }),
              }}
            />
          ),
        )}
      </>
    );
  }

  const visible = stations.filter((s) => bounds.pad(0.25).contains([s.lat, s.lon]));
  return (
    <>
      {visible.map((station) => (
        <StationMarker
          key={station.station_id}
          station={station}
          theme={theme}
          openId={openId}
          setOpenId={setOpenId}
        />
      ))}
    </>
  );
}

function StationMarker({
  station,
  theme,
  openId,
  setOpenId,
}: {
  station: StationSummary;
  theme: "light" | "dark";
  openId: number | null;
  setOpenId: (id: number | null) => void;
}) {
  const color = ETAT_COLORS[station.etat];
  const center: [number, number] = [station.lat, station.lon];
  return (
    <>
      {/* Halo discret sous le marqueur : approximation d'une ombre légère
          (le rendu canvas de Leaflet ne gère pas les ombres portées). */}
      <CircleMarker
        center={center}
        radius={7.5}
        interactive={false}
        pathOptions={{ stroke: false, fillColor: "#000", fillOpacity: theme === "dark" ? 0.35 : 0.14 }}
      />
      <CircleMarker
        center={center}
        radius={5.5}
        pathOptions={{ color: "#ffffff", fillColor: color, fillOpacity: 1, weight: 1.75 }}
        eventHandlers={{
          mouseover: (e) => e.target.openPopup(),
          popupopen: () => setOpenId(station.station_id),
          popupclose: () => setOpenId(null),
        }}
      >
        <Popup minWidth={210} closeButton={false}>
          <StationPopup station={station} active={openId === station.station_id} />
        </Popup>
      </CircleMarker>
    </>
  );
}

function LocateControl() {
  const map = useMap();
  const [position, setPosition] = useState<L.LatLng | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const buttonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (buttonRef.current) {
      L.DomEvent.disableClickPropagation(buttonRef.current);
      L.DomEvent.disableScrollPropagation(buttonRef.current);
    }
  }, []);

  useMapEvents({
    locationfound: (e) => {
      setPosition(e.latlng);
      setMessage(null);
    },
    locationerror: () => setMessage("Localisation refusée ou indisponible."),
  });

  return (
    <>
      <div ref={buttonRef} className="locate-control">
        <button type="button" className="locate-btn" onClick={() => map.locate({ setView: true, maxZoom: 16 })}>
          <LocateFixed size={16} aria-hidden="true" />
          Me localiser
        </button>
        {message && (
          <span className="locate-msg" role="alert">
            {message}
          </span>
        )}
      </div>
      {position && (
        <>
          <CircleMarker
            center={position}
            radius={16}
            interactive={false}
            pathOptions={{ stroke: false, fillColor: "#2a78d6", fillOpacity: 0.18 }}
          />
          <CircleMarker
            center={position}
            radius={6}
            interactive={false}
            pathOptions={{ color: "#ffffff", weight: 2, fillColor: "#2a78d6", fillOpacity: 1 }}
          />
        </>
      )}
    </>
  );
}

export function StationMap({ stations }: { stations: StationSummary[] }) {
  return (
    <MapContainer
      center={PARIS_CENTER}
      zoom={12}
      preferCanvas
      style={{ height: "100%", width: "100%", borderRadius: "var(--radius-lg)" }}
    >
      <TileLayer attribution={ATTRIBUTION} url={TILE_URL} maxZoom={19} />
      <Markers stations={stations} />
      <LocateControl />
    </MapContainer>
  );
}
