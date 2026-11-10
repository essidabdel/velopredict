import { ETAT_COLORS, ETAT_LABELS, ETAT_ORDER } from "../constants/etat";

export function MapLegend() {
  return (
    <div
      className="card"
      aria-label="Légende de la carte"
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "var(--space-4)",
        alignItems: "center",
        padding: "var(--space-3) var(--space-4)",
      }}
    >
      {ETAT_ORDER.map((etat) => (
        <span
          key={etat}
          style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-2)" }}
        >
          <span
            aria-hidden="true"
            style={{
              width: 12,
              height: 12,
              borderRadius: "50%",
              background: ETAT_COLORS[etat],
              display: "inline-block",
            }}
          />
          <span style={{ fontSize: "0.9rem" }}>{ETAT_LABELS[etat]}</span>
        </span>
      ))}
    </div>
  );
}
