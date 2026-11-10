import type { NiveauRisque } from "../api/types";
import { NIVEAU_RISQUE_COLORS, NIVEAU_RISQUE_LABELS } from "../constants/etat";

// Niveau discret uniquement — jamais une probabilité brute (consigne
// explicite du projet).
export function RiskBadge({ niveau }: { niveau: NiveauRisque }) {
  const color = NIVEAU_RISQUE_COLORS[niveau];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "var(--space-2)",
        padding: "var(--space-1) var(--space-3)",
        borderRadius: "var(--radius)",
        background: color,
        color: niveau === "moyen" ? "#2a1800" : "#ffffff",
        fontWeight: 650,
        fontSize: "0.9rem",
      }}
    >
      Risque de pénurie (30 min) : {NIVEAU_RISQUE_LABELS[niveau]}
    </span>
  );
}
