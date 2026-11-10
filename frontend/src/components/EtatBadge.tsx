import type { EtatStation } from "../api/types";
import { ETAT_COLORS, ETAT_LABELS } from "../constants/etat";

export function EtatBadge({ etat }: { etat: EtatStation }) {
  const color = ETAT_COLORS[etat];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "var(--space-2)",
        padding: "2px var(--space-2) 2px 2px",
        borderRadius: 999,
        border: "1px solid var(--border)",
        fontSize: "0.85rem",
        fontWeight: 600,
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: color,
          display: "inline-block",
        }}
      />
      {ETAT_LABELS[etat]}
    </span>
  );
}
