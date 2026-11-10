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
      <h1 className="page-title">Carte des stations</h1>
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        <FilterBar filters={filters} onChange={setFilters} />
        <MapLegend />

        {error && <ErrorState message={error} onRetry={reload} />}
        {!error && loading && !stations && <LoadingState label="Chargement des stations…" />}
        {!error && stations && (
          <>
            <p className="text-muted" style={{ margin: 0 }}>
              {stations.length} station{stations.length > 1 ? "s" : ""} — actualisation
              automatique toutes les 60 secondes.
            </p>
            <div style={{ height: "min(70vh, 640px)", minHeight: 360 }}>
              <StationMap stations={stations} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
