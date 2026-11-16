import { ArrowDownRight, ArrowRight, ArrowUpRight, Info } from "lucide-react";
import type { NiveauRisque, StationPrediction } from "../api/types";
import { NIVEAU_RISQUE_COLORS } from "../constants/etat";
import { formatNumber, pluralVelos } from "../lib/format";
import { RiskBadge } from "./RiskBadge";

// Le modèle renvoie des valeurs réelles (ex. 3,47) : on affiche un nombre
// entier de vélos, borné entre 0 et la capacité de la station.
export function toBikeCount(value: number, capacity: number): number {
  const rounded = Math.round(value);
  return Math.min(Math.max(rounded, 0), Math.max(capacity, 0));
}

const RISK_SENTENCES: Record<NiveauRisque, string> = {
  eleve: "Il risque de n'y avoir plus aucun vélo dans 30 min.",
  moyen: "Il pourrait ne rester que peu de vélos dans 30 min.",
  faible: "Vous devriez trouver un vélo dans 30 min.",
};

interface Props {
  prediction: StationPrediction;
  capacity: number;
}

export function PredictionPanel({ prediction, capacity }: Props) {
  const now = toBikeCount(prediction.bikes_now, capacity);
  const in30 = toBikeCount(prediction.prediction_30min, capacity);
  const in60 = toBikeCount(prediction.prediction_60min, capacity);
  const riskColor = NIVEAU_RISQUE_COLORS[prediction.risk_level_30min];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: "var(--space-3)",
        }}
      >
        <Tile label="Maintenant" value={now} />
        <Tile label="Dans 30 min" value={in30} delta={in30 - now} highlight />
        <Tile label="Dans 1 h" value={in60} delta={in60 - now} highlight />
      </div>

      <div
        style={{
          borderLeft: `4px solid ${riskColor}`,
          background: `${riskColor}14`,
          borderRadius: "var(--radius-sm)",
          padding: "var(--space-3) var(--space-4)",
          display: "flex",
          flexDirection: "column",
          gap: "var(--space-2)",
          alignItems: "flex-start",
        }}
      >
        <RiskBadge niveau={prediction.risk_level_30min} />
        <span style={{ fontWeight: 600 }}>{RISK_SENTENCES[prediction.risk_level_30min]}</span>
      </div>

      <p
        className="text-muted"
        style={{ margin: 0, fontSize: "0.8rem", display: "flex", gap: 6, alignItems: "flex-start" }}
      >
        <Info size={14} style={{ flexShrink: 0, marginTop: 2 }} />
        Estimation (vélos mécaniques + électriques) : une prévision, pas une certitude.
      </p>
    </div>
  );
}

function Tile({
  label,
  value,
  delta,
  highlight = false,
}: {
  label: string;
  value: number;
  delta?: number;
  highlight?: boolean;
}) {
  const Trend = delta === undefined || delta === 0 ? ArrowRight : delta > 0 ? ArrowUpRight : ArrowDownRight;
  const trendColor =
    delta === undefined || delta === 0
      ? "var(--text-muted)"
      : delta > 0
        ? "var(--status-good)"
        : "var(--status-critical)";
  const trendText =
    delta === undefined
      ? null
      : delta === 0
        ? "Stable"
        : `${delta > 0 ? "+" : "−"}${Math.abs(delta)} ${pluralVelos(delta)}`;

  return (
    <div
      style={{
        background: highlight ? "var(--brand-ring)" : "var(--surface-2)",
        border: highlight ? "1px solid var(--brand)" : "1px solid var(--border)",
        borderRadius: "var(--radius)",
        padding: "var(--space-3) var(--space-4)",
      }}
    >
      <div className="text-muted" style={{ fontSize: "0.8rem", fontWeight: 600 }}>
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
        <span
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "2.4rem",
            fontWeight: 800,
            lineHeight: 1.1,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {formatNumber(value)}
        </span>
        <span className="text-secondary" style={{ fontSize: "0.9rem" }}>
          {pluralVelos(value)}
        </span>
      </div>
      {trendText && (
        <div
          style={{ display: "flex", alignItems: "center", gap: 4, color: trendColor, fontSize: "0.82rem", fontWeight: 600 }}
        >
          <Trend size={14} />
          {trendText}
        </div>
      )}
    </div>
  );
}
