import { Activity, Battery, Bike, Gauge, MapPin, TrendingUp } from "lucide-react";
import { useCallback } from "react";
import { useParams } from "react-router-dom";
import { fetchStation, fetchStationHistory, fetchStationPrediction } from "../api/client";
import { AvailabilityChart } from "../components/AvailabilityChart";
import { EtatBadge } from "../components/EtatBadge";
import { ErrorState } from "../components/ErrorState";
import { RiskBadge } from "../components/RiskBadge";
import { ChartCardSkeleton, Skeleton } from "../components/Skeleton";
import { useResource } from "../hooks/useResource";

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
        <h1 className="page-title" style={{ marginBottom: "var(--space-2)" }}>
          <span className="page-title-icon">
            <Bike size={22} />
          </span>
          {station.name}
        </h1>
        <p
          className="text-secondary"
          style={{ margin: 0, display: "flex", alignItems: "center", gap: 6, paddingLeft: 2 }}
        >
          <MapPin size={15} />
          {station.commune_nom ?? "Commune inconnue"} · Capacité {station.capacity} places
        </p>
      </div>

      <section className="card">
        <h2 className="section-title">
          <Activity size={18} />
          État actuel
        </h2>
        <div
          style={{ display: "flex", gap: "var(--space-5)", flexWrap: "wrap", alignItems: "center" }}
        >
          <EtatBadge etat={station.etat} />
          {station.num_mechanical !== null && <Stat label="Mécaniques" value={station.num_mechanical} />}
          {station.num_ebike !== null && <Stat label="Électriques" value={station.num_ebike} />}
          {station.num_docks_available !== null && (
            <Stat label="Bornes libres" value={station.num_docks_available} />
          )}
        </div>
      </section>

      <section className="card">
        <h2 className="section-title">
          <Gauge size={18} />
          Dernières 24 heures
        </h2>
        {errorHistory && <ErrorState message={errorHistory} />}
        {!errorHistory && loadingHistory && <Skeleton height={220} radius="var(--radius)" />}
        {!errorHistory && history && history.length === 0 && (
          <p className="text-muted">Pas encore assez d'historique pour cette station.</p>
        )}
        {!errorHistory && history && history.length > 0 && (
          <AvailabilityChart history={history} capacity={station.capacity} />
        )}
      </section>

      <section className="card">
        <h2 className="section-title">
          <TrendingUp size={18} />
          Prédiction
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
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <div style={{ display: "flex", gap: "var(--space-5)", flexWrap: "wrap" }}>
              <Stat label="Maintenant" value={prediction.bikes_now} />
              <Stat label="Dans 30 min" value={prediction.prediction_30min} />
              <Stat label="Dans 60 min" value={prediction.prediction_60min} />
            </div>
            <div>
              <RiskBadge niveau={prediction.risk_level_30min} />
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1.4rem",
          fontWeight: 700,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {value}
      </div>
      <div className="text-muted" style={{ fontSize: "0.8rem" }}>
        {label}
      </div>
    </div>
  );
}
