import type { EtatStation } from "../api/types";
import { ETAT_COLORS, ETAT_LABELS } from "../constants/etat";

export function EtatBadge({ etat }: { etat: EtatStation }) {
  const color = ETAT_COLORS[etat];
  return (
    <span className="chip" style={{ background: `${color}1c`, color }}>
      <span className="chip-dot" aria-hidden="true" style={{ background: color }} />
      {ETAT_LABELS[etat]}
    </span>
  );
}
