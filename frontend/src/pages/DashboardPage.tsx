import { fetchStations, fetchStatsOverview } from "../api/client";
import {
  BikeTypeChart,
  EtatBreakdownChart,
  TopCommunesVidesChart,
} from "../components/DashboardCharts";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { StatTile } from "../components/StatTile";
import { useResource } from "../hooks/useResource";

const POLL_MS = 60_000;

const statsFetcher = () => fetchStatsOverview();
const stationsFetcher = () => fetchStations({});

export function DashboardPage() {
  const {
    data: stats,
    loading: loadingStats,
    error: errorStats,
    reload: reloadStats,
  } = useResource("dashboard:stats", statsFetcher, { pollMs: POLL_MS });

  const {
    data: stations,
    loading: loadingStations,
    error: errorStations,
    reload: reloadStations,
  } = useResource("dashboard:stations", stationsFetcher, { pollMs: POLL_MS });

  const loading = (loadingStats && !stats) || (loadingStations && !stations);
  const error = errorStats ?? errorStations;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
      <h1 className="page-title">Tableau de bord</h1>

      {error && <ErrorState message={error} onRetry={() => { reloadStats(); reloadStations(); }} />}
      {!error && loading && <LoadingState label="Chargement du tableau de bord…" />}

      {!error && stats && (
        <section style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-4)" }}>
          <StatTile label="Vélos disponibles (réseau)" value={stats.total_bikes_available} />
          <StatTile
            label="Stations vides"
            value={stats.nb_stations_vides}
            accent="var(--status-critical)"
          />
          <StatTile
            label="Stations pleines"
            value={stats.nb_stations_pleines}
            accent="var(--series-1)"
          />
          <StatTile label="Stations suivies" value={`${stats.nb_stations_avec_etat} / ${stats.nb_stations}`} />
        </section>
      )}

      {!error && stations && (
        <>
          <section className="card">
            <h2 className="section-title">Répartition des stations par état</h2>
            <EtatBreakdownChart stations={stations} />
          </section>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
              gap: "var(--space-4)",
            }}
          >
            {stats && (
              <section className="card">
                <h2 className="section-title">Vélos mécaniques vs électriques</h2>
                <BikeTypeChart stats={stats} />
              </section>
            )}
            <section className="card">
              <h2 className="section-title">Communes avec le plus de stations vides</h2>
              <p className="text-muted" style={{ marginTop: 0, fontSize: "0.85rem" }}>
                Instantané actuel — pas une moyenne historique.
              </p>
              <TopCommunesVidesChart stations={stations} />
            </section>
          </div>
        </>
      )}
    </div>
  );
}
