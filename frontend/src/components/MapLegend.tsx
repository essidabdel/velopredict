import type { EtatStation } from "../api/types";
import { ETAT_COLORS, ETAT_LABELS, ETAT_ORDER } from "../constants/etat";
import { formatNumber } from "../lib/format";

// Légende = filtres : un clic masque / affiche les stations de cet état sur
// la carte (le compteur reste celui de la sélection courante).
export function MapLegend({
  counts,
  hidden,
  onToggle,
  floating = false,
}: {
  counts: Record<EtatStation, number>;
  hidden: Set<EtatStation>;
  onToggle: (etat: EtatStation) => void;
  floating?: boolean;
}) {
  return (
    <div
      role="group"
      aria-label="Filtrer la carte par état"
      className={floating ? "map-overlay map-legend-overlay" : "card"}
    >
      {ETAT_ORDER.filter((etat) => etat !== "inconnue" || counts.inconnue > 0).map((etat) => {
        const color = ETAT_COLORS[etat];
        const off = hidden.has(etat);
        return (
          <button
            key={etat}
            type="button"
            className="legend-filter"
            aria-pressed={!off}
            onClick={() => onToggle(etat)}
            title={off ? `Afficher : ${ETAT_LABELS[etat]}` : `Masquer : ${ETAT_LABELS[etat]}`}
            style={{ opacity: off ? 0.5 : 1 }}
          >
            <span
              className="chip-dot"
              aria-hidden="true"
              style={{ background: off ? "transparent" : color, border: `2px solid ${color}` }}
            />
            <span>{ETAT_LABELS[etat]}</span>
            <strong>{formatNumber(counts[etat])}</strong>
          </button>
        );
      })}
    </div>
  );
}
