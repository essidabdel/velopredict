import { MapIcon, RadioTower, SearchX } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { fetchStations } from "../api/client";
import type { EtatStation } from "../api/types";
import { UpdatedAgo } from "../components/UpdatedAgo";
import { ETAT_ORDER } from "../constants/etat";
import { formatNumber } from "../lib/format";
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
    updatedAt,
    reload,
  } = useResource(`stations:${JSON.stringify(filters)}`, fetcher, { pollMs: POLL_MS });

  const [hidden, setHidden] = useState<Set<EtatStation>>(new Set());
  const toggle = (etat: EtatStation) =>
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(etat)) next.delete(etat);
      else next.add(etat);
      return next;
    });

  const counts = useMemo(() => {
    const c = Object.fromEntries(ETAT_ORDER.map((e) => [e, 0])) as Record<EtatStation, number>;
    for (const s of stations ?? []) c[s.etat] += 1;
    return c;
  }, [stations]);
  const shown = useMemo(() => (stations ?? []).filter((s) => !hidden.has(s.etat)), [stations, hidden]);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">
          <span className="page-title-icon">
            <MapIcon size={22} />
          </span>
          Carte des stations
        </h1>
        <UpdatedAgo at={updatedAt} />
      </div>
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
          <div className="map-fullbleed">
            <div className="map-wrap rise-in" style={{ height: "min(80vh, 780px)", minHeight: 420 }}>
              <StationMap stations={shown} />
              <MapLegend counts={counts} hidden={hidden} onToggle={toggle} floating />
              <span className="map-overlay map-count-overlay chip" style={{ color: "var(--text-secondary)" }}>
                <RadioTower size={14} />
                {formatNumber(shown.length)} station{shown.length > 1 ? "s" : ""} affichée
                {shown.length > 1 ? "s" : ""} · actualisées chaque minute
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
