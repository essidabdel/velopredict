import { ETAT_COLORS, ETAT_LABELS, ETAT_ORDER } from "../constants/etat";

export function MapLegend() {
  return (
    <div
      className="card"
      aria-label="Légende de la carte"
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "var(--space-2)",
        alignItems: "center",
        padding: "var(--space-3) var(--space-4)",
      }}
    >
      {ETAT_ORDER.map((etat) => {
        const color = ETAT_COLORS[etat];
        return (
          <span
            key={etat}
            className="chip"
            style={{ background: `${color}1c`, color }}
          >
            <span className="chip-dot" aria-hidden="true" style={{ background: color }} />
            <span style={{ color: "var(--text-secondary)" }}>{ETAT_LABELS[etat]}</span>
          </span>
        );
      })}
    </div>
  );
}
