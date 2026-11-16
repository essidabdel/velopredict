import { AlertTriangle, ShieldAlert, ShieldCheck } from "lucide-react";
import type { NiveauRisque } from "../api/types";
import { NIVEAU_RISQUE_COLORS, NIVEAU_RISQUE_LABELS } from "../constants/etat";

const ICONS: Record<NiveauRisque, typeof ShieldCheck> = {
  eleve: AlertTriangle,
  moyen: ShieldAlert,
  faible: ShieldCheck,
};

// Niveau discret uniquement — jamais une probabilité brute (consigne
// explicite du projet).
export function RiskBadge({ niveau }: { niveau: NiveauRisque }) {
  const color = NIVEAU_RISQUE_COLORS[niveau];
  const Icon = ICONS[niveau];
  return (
    <span
      className="chip"
      style={{
        background: color,
        color: niveau === "moyen" ? "#2a1800" : "#ffffff",
        padding: "9px 16px",
        fontSize: "0.92rem",
        boxShadow: `0 8px 18px -6px ${color}99`,
      }}
    >
      <Icon size={16} />
      Risque de pénurie : {NIVEAU_RISQUE_LABELS[niveau].toLowerCase()}
    </span>
  );
}
