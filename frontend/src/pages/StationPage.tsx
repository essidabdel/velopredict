import { Activity, Battery, Bike, Gauge, MapPin, TrendingUp } from "lucide-react";
import { useCallback } from "react";
import { useParams } from "react-router-dom";
import { fetchStation, fetchStationHistory, fetchStationPrediction } from "../api/client";
import { AnimatedNumber } from "../components/AnimatedNumber";
import { AvailabilityChart } from "../components/AvailabilityChart";
import { EtatBadge } from "../components/EtatBadge";
import { ErrorState } from "../components/ErrorState";
import { PredictionPanel } from "../components/PredictionPanel";
import { ChartCardSkeleton, Skeleton } from "../components/Skeleton";
import { FillGauge } from "../components/FillGauge";
import { UpdatedAgo } from "../components/UpdatedAgo";
import { ETAT_EXPLICATIONS } from "../constants/etat";
import { useResource } from "../hooks/useResource";
import { formatNumber, shortCommune } from "../lib/format";

const POLL_MS = 60_000;

export function StationPage() {
  const { stationId } = useParams();
  const id = Number(stationId);
  const validId = Number.isFinite(id);

  const stationFetcher = useCallback(() => fetchStation(id), [id]);
  const {
    data: station,
    loading: loadingStation,
    error: errorStation,
    updatedAt,
    reload: reloadStation,
  } = useResource(`station:${id}`, stationFetcher, { pollMs: POLL_MS });

  const historyFetcher = useCallback(() => fetchStationHistory(id, 24), [id]);
  const { data: history, loading: loadingHistory, error: errorHistory } = useResource(
    `history:${id}`,
    historyFetcher,
  );

  const predictionFetcher = useCallback(() => fetchStationPrediction(id), [id]);
  const {
    data: prediction,
    loading: loadingPrediction,
    error: errorPrediction,
  } = useResource(`prediction:${id}`, predictionFetcher, { pollMs: POLL_MS });

  if (!validId) {
    return <ErrorState message="Identifiant de station invalide." />;
  }

  if (errorStation) {
    return <ErrorState message={errorStation} onRetry={reloadStation} />;
  }

  if (loadingStation && !station) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
        <div>
          <Skeleton width="55%" height={32} style={{ marginBottom: "var(--space-2)" }} />
          <Skeleton width="35%" height={16} />
        </div>
        <ChartCardSkeleton height={60} />
        <ChartCardSkeleton height={220} />
        <ChartCardSkeleton height={60} />
      </div>
    );
  }

  if (!station) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
      <div>
        <div className="page-header" style={{ marginBottom: "var(--space-2)" }}>
          <h1 className="page-title" style={{ margin: 0 }}>
            <span className="page-title-icon">
              <Bike size={22} />
            </span>
            {station.name}
          </h1>
          <UpdatedAgo at={updatedAt} />
        </div>
        <p
          className="text-secondary"
          style={{ margin: 0, display: "flex", alignItems: "center", gap: 6, paddingLeft: 2 }}
        >
          <MapPin size={15} />
          {shortCommune(station.commune_nom)} · {formatNumber(station.capacity)} places au total
        </p>
      </div>

      <section className="card">
        <h2 className="section-title">
          <Activity size={18} />
          En ce moment
        </h2>
        <div className="station-now">
          <div style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 220, flex: "1 1 240px" }}>
            <div>
              <EtatBadge etat={station.etat} />
            </div>
            <span className="text-secondary" style={{ fontSize: "0.88rem" }}>
              {ETAT_EXPLICATIONS[station.etat]}
            </span>
            {station.num_mechanical !== null && station.num_ebike !== null && (
              <FillGauge
                bikes={station.num_mechanical + station.num_ebike}
                capacity={station.capacity}
                etat={station.etat}
              />
            )}
          </div>
          <div className="station-stats">
            {station.num_mechanical !== null && <Stat label="Vélos mécaniques" value={station.num_mechanical} />}
            {station.num_ebike !== null && <Stat label="Vélos électriques" value={station.num_ebike} />}
            {station.num_docks_available !== null && (
              <Stat label="Bornes libres" value={station.num_docks_available} />
            )}
          </div>
        </div>
      </section>

      <section className="card">
        <h2 className="section-title">
          <Gauge size={18} />
          Dernières 24 h
        </h2>
        {errorHistory && <ErrorState message={errorHistory} />}
        {!errorHistory && loadingHistory && <Skeleton height={220} radius="var(--radius)" />}
        {!errorHistory && history && history.length === 0 && (
          <p className="text-muted">Pas encore assez d'historique pour cette station.</p>
        )}
        {!errorHistory && history && history.length > 0 && (
          <AvailabilityChart history={history} capacity={station.capacity} prediction={prediction} />
        )}
      </section>

      <section className="card">
        <h2 className="section-title">
          <TrendingUp size={18} />
          Prévisions
        </h2>
        {errorPrediction && (
          <p className="text-muted" style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Battery size={15} />
            Prédiction indisponible : {errorPrediction}
          </p>
        )}
        {!errorPrediction && loadingPrediction && (
          <div style={{ display: "flex", gap: "var(--space-5)", flexWrap: "wrap" }}>
            <Skeleton width={70} height={34} />
            <Skeleton width={70} height={34} />
            <Skeleton width={70} height={34} />
          </div>
        )}
        {!errorPrediction && prediction && (
          <PredictionPanel prediction={prediction} capacity={station.capacity} />
        )}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="stat-value" style={{ fontSize: "1.5rem" }}>
        <AnimatedNumber value={value} />
      </div>
      <div className="stat-label">
        {label}
      </div>
    </div>
  );
}
