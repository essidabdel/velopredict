import { MapIcon, RadioTower, SearchX } from "lucide-react";
import { useCallback } from "react";
import { fetchStations } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import { FilterBar } from "../components/FilterBar";
import { LoadingState } from "../components/LoadingState";
import { MapLegend } from "../components/MapLegend";
import { StationMap } from "../components/StationMap";
import { useResource } from "../hooks/useResource";
import { useUrlFilters } from "../hooks/useUrlFilters";

const POLL_MS = 60_000;

export function MapPage() {
  const { filters, setFilters } = useUrlFilters();

  const fetcher = useCallback(() => fetchStations(filters), [filters]);
  const {
    data: stations,
    loading,
    error,
    reload,
  } = useResource(`stations:${JSON.stringify(filters)}`, fetcher, { pollMs: POLL_MS });

  return (
    <div>
      <h1 className="page-title">
        <span className="page-title-icon">
          <MapIcon size={22} />
        </span>
        Carte des stations
      </h1>
      <p className="page-lede">
        La disponibilité des vélos Vélib', station par station, autour de Paris.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        <FilterBar filters={filters} onChange={setFilters} />

        {error && <ErrorState message={error} onRetry={reload} />}
        {!error && loading && !stations && <LoadingState label="Chargement des stations…" />}
        {!error && stations && stations.length === 0 && (
          <div className="card empty-state">
            <span
              className="icon-badge"
              style={{
                background: "color-mix(in srgb, var(--brand) 12%, transparent)",
                color: "var(--brand)",
              }}
            >
              <SearchX size={22} />
            </span>
            <p style={{ margin: 0, fontWeight: 650, color: "var(--text-primary)" }}>
              Aucune station ne correspond à ces filtres
            </p>
            <p style={{ margin: 0 }}>Essaie d'élargir la recherche ou réinitialise les filtres.</p>
          </div>
        )}
        {!error && stations && stations.length > 0 && (
          <div className="map-wrap rise-in" style={{ height: "min(78vh, 760px)", minHeight: 420 }}>
            <StationMap stations={stations} />
            <MapLegend floating />
            <span className="map-overlay map-count-overlay chip" style={{ color: "var(--brand-dark)" }}>
              <RadioTower size={14} />
              {stations.length} station{stations.length > 1 ? "s" : ""} · maj 60s
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
