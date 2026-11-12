import { Bike, CircleParking, LayoutDashboard, PieChart, Radar } from "lucide-react";
import { fetchStations, fetchStatsOverview } from "../api/client";
import {
  BikeTypeChart,
  StatusCompositionBar,
  TopCommunesVidesChart,
} from "../components/DashboardCharts";
import { ErrorState } from "../components/ErrorState";
import { ChartCardSkeleton, StatTileSkeleton } from "../components/Skeleton";
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
      <h1 className="page-title">
        <span className="page-title-icon">
          <LayoutDashboard size={22} />
        </span>
        Tableau de bord
      </h1>
      <p className="page-lede">Vue d'ensemble du réseau Vélib', mise à jour toutes les 60 secondes.</p>

      {error && <ErrorState message={error} onRetry={() => { reloadStats(); reloadStations(); }} />}

      {!error && loading && (
        <>
          <section style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-4)" }}>
            <StatTileSkeleton key="skel-bikes" />
            <StatTileSkeleton key="skel-vides" />
            <StatTileSkeleton key="skel-pleines" />
            <StatTileSkeleton key="skel-suivies" />
          </section>
          <ChartCardSkeleton />
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
              gap: "var(--space-4)",
            }}
          >
            <ChartCardSkeleton height={160} />
            <ChartCardSkeleton height={160} />
          </div>
        </>
      )}

      {!error && stats && (
        <section className="rise-in" style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-4)" }}>
          <StatTile
            label="Vélos disponibles (réseau)"
            value={stats.total_bikes_available}
            accent="var(--status-good)"
            icon={<Bike size={20} />}
          />
          <StatTile
            label="Stations vides"
            value={stats.nb_stations_vides}
            accent="var(--status-critical)"
            icon={<CircleParking size={20} />}
          />
          <StatTile
            label="Stations pleines"
            value={stats.nb_stations_pleines}
            accent="var(--series-1)"
            icon={<CircleParking size={20} />}
          />
          <StatTile
            label="Stations suivies"
            value={`${stats.nb_stations_avec_etat} / ${stats.nb_stations}`}
            accent="var(--brand)"
            icon={<Radar size={20} />}
          />
        </section>
      )}

      {!error && stations && (
        <>
          <section className="card rise-in">
            <h2 className="section-title">
              <PieChart size={18} />
              Répartition des stations par état
            </h2>
            <StatusCompositionBar stations={stations} />
          </section>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
              gap: "var(--space-4)",
            }}
          >
            {stats && (
              <section className="card rise-in">
                <h2 className="section-title">
                  <Bike size={18} />
                  Vélos mécaniques vs électriques
                </h2>
                <BikeTypeChart stats={stats} />
              </section>
            )}
            <section className="card rise-in">
              <h2 className="section-title">
                <CircleParking size={18} />
                Communes avec le plus de stations vides
              </h2>
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
