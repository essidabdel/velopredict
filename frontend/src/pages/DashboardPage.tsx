import { Bike, CircleParking, Eye, LayoutDashboard, PieChart, Radar } from "lucide-react";
import { fetchStations, fetchStatsOverview } from "../api/client";
import {
  BikeTypeChart,
  StatusCompositionBar,
  TopCommunesVidesChart,
} from "../components/DashboardCharts";
import { ErrorState } from "../components/ErrorState";
import { ChartCardSkeleton, StatTileSkeleton } from "../components/Skeleton";
import { StatTile } from "../components/StatTile";
import { UpdatedAgo } from "../components/UpdatedAgo";
import { WatchList } from "../components/WatchList";
import { useResource } from "../hooks/useResource";
import { formatNumber, formatPercent } from "../lib/format";

const POLL_MS = 60_000;

const statsFetcher = () => fetchStatsOverview();
const stationsFetcher = () => fetchStations({});

export function DashboardPage() {
  const {
    data: stats,
    loading: loadingStats,
    error: errorStats,
    updatedAt: statsUpdatedAt,
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

  const totalCapacity = stations?.reduce((sum, s) => sum + s.capacity, 0) ?? 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
      <div className="page-header">
        <h1 className="page-title">
          <span className="page-title-icon">
            <LayoutDashboard size={22} />
          </span>
          Tableau de bord
        </h1>
        <UpdatedAgo at={statsUpdatedAt} />
      </div>
      <p className="page-lede">Vue d'ensemble du réseau Vélib', mise à jour toutes les 60 secondes.</p>

      {error && <ErrorState message={error} onRetry={() => { reloadStats(); reloadStations(); }} />}

      {!error && loading && (
        <>
          <section className="kpi-grid">
            <StatTileSkeleton key="skel-bikes" />
            <StatTileSkeleton key="skel-vides" />
            <StatTileSkeleton key="skel-pleines" />
            <StatTileSkeleton key="skel-suivies" />
          </section>
          <ChartCardSkeleton />
          <div className="chart-grid">
            <ChartCardSkeleton height={160} />
            <ChartCardSkeleton height={160} />
          </div>
        </>
      )}

      {!error && stats && (
        <section className="kpi-grid rise-in">
          <StatTile
            label="vélos disponibles"
            value={stats.total_bikes_available}
            sub={totalCapacity > 0 ? `${formatPercent(stats.total_bikes_available, totalCapacity)} de la capacité` : undefined}
            accent="var(--status-good)"
            icon={<Bike size={20} />}
          />
          <StatTile
            label="stations vides"
            value={stats.nb_stations_vides}
            sub={`${formatNumber(stats.nb_stations_vides)} sur ${formatNumber(stats.nb_stations_avec_etat)} · ${formatPercent(stats.nb_stations_vides, stats.nb_stations_avec_etat)}`}
            accent="var(--status-critical)"
            icon={<CircleParking size={20} />}
          />
          <StatTile
            label="stations pleines"
            value={stats.nb_stations_pleines}
            sub={`${formatNumber(stats.nb_stations_pleines)} sur ${formatNumber(stats.nb_stations_avec_etat)} · ${formatPercent(stats.nb_stations_pleines, stats.nb_stations_avec_etat)}`}
            accent="var(--series-1)"
            icon={<CircleParking size={20} />}
          />
          <StatTile
            label="stations suivies"
            value={stats.nb_stations_avec_etat}
            sub={`${formatPercent(stats.nb_stations_avec_etat, stats.nb_stations)} du réseau`}
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

          <div className="chart-grid">
            {stats && (
              <section className="card rise-in">
                <h2 className="section-title">
                  <Bike size={18} />
                  Mécaniques et électriques
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
                En ce moment
              </p>
              <TopCommunesVidesChart stations={stations} />
            </section>
          </div>

          <section className="card rise-in">
            <h2 className="section-title">
              <Eye size={18} />
              Stations à surveiller
            </h2>
            <p className="text-muted" style={{ marginTop: 0, fontSize: "0.85rem" }}>
              Risque de pénurie le plus élevé dans 30 minutes
            </p>
            <WatchList stations={stations} />
          </section>
        </>
      )}
    </div>
  );
}
