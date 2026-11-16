import { AlertTriangle, ChevronRight } from "lucide-react";
import { useCallback } from "react";
import { Link } from "react-router-dom";
import { fetchStationPrediction } from "../api/client";
import type { NiveauRisque, StationPrediction, StationSummary } from "../api/types";
import { ETAT_COLORS, NIVEAU_RISQUE_COLORS, NIVEAU_RISQUE_LABELS } from "../constants/etat";
import { useResource } from "../hooks/useResource";
import { shortCommune } from "../lib/format";
import { toBikeCount } from "./PredictionPanel";
import { Skeleton } from "./Skeleton";

const CANDIDATES = 12;
const RISK_RANK: Record<NiveauRisque, number> = { eleve: 0, moyen: 1, faible: 2 };

interface Row {
  station: StationSummary;
  prediction: StationPrediction;
}

// « Stations à surveiller » : l'API ne fournit pas de classement global des
// risques. On prend donc, parmi les stations actuellement « presque vides »,
// les 12 les plus basses, on demande leur prévision à 30 min (12 appels, pas
// 1 500), puis on garde les 5 au risque de pénurie le plus élevé.
export function WatchList({ stations }: { stations: StationSummary[] }) {
  const candidates = stations
    .filter((s) => s.etat === "faible" && s.is_renting !== false)
    .sort((a, b) => (a.num_mechanical ?? 0) + (a.num_ebike ?? 0) - ((b.num_mechanical ?? 0) + (b.num_ebike ?? 0)))
    .slice(0, CANDIDATES);
  const key = `watch:${candidates.map((s) => s.station_id).join(",")}`;

  const fetcher = useCallback(async (): Promise<Row[]> => {
    const results = await Promise.all(
      candidates.map(async (station) => {
        try {
          return { station, prediction: await fetchStationPrediction(station.station_id) };
        } catch {
          return null; // prévision indisponible : on ignore la station
        }
      }),
    );
    return results
      .filter((r): r is Row => r !== null)
      .sort(
        (a, b) =>
          RISK_RANK[a.prediction.risk_level_30min] - RISK_RANK[b.prediction.risk_level_30min] ||
          a.prediction.prediction_30min - b.prediction.prediction_30min,
      )
      .slice(0, 5);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const { data, loading, error } = useResource(key, fetcher);

  if (loading && !data) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
        {[0, 1, 2, 3, 4].map((i) => (
          <Skeleton key={i} height={52} radius="var(--radius)" />
        ))}
      </div>
    );
  }
  if (error || !data || data.length === 0) {
    return <p className="text-muted">Aucune station à surveiller pour le moment.</p>;
  }

  return (
    <ul className="watch-list">
      {data.map(({ station, prediction }) => {
        const capacity = station.capacity;
        const now = toBikeCount(prediction.bikes_now, capacity);
        const in30 = toBikeCount(prediction.prediction_30min, capacity);
        const color = NIVEAU_RISQUE_COLORS[prediction.risk_level_30min];
        return (
          <li key={station.station_id}>
            <Link to={`/stations/${station.station_id}`} className="watch-item">
              <span className="watch-dot" aria-hidden="true" style={{ background: ETAT_COLORS.faible }} />
              <span className="watch-main">
                <span className="watch-name">{station.name}</span>
                <span className="text-muted watch-sub">
                  {shortCommune(station.commune_nom)} · {now} → {in30} vélo{in30 > 1 ? "s" : ""} dans 30 min
                </span>
              </span>
              <span className="chip" style={{ background: `${color}22`, color: "var(--text-primary)" }}>
                <AlertTriangle size={12} style={{ color }} aria-hidden="true" />
                Risque {NIVEAU_RISQUE_LABELS[prediction.risk_level_30min].toLowerCase()}
              </span>
              <ChevronRight size={16} aria-hidden="true" className="text-muted" />
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
