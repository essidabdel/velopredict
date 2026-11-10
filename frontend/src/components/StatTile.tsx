export function StatTile({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: string;
}) {
  return (
    <div className="card" style={{ minWidth: 140, flex: "1 1 140px" }}>
      <div
        style={{
          fontSize: "1.8rem",
          fontWeight: 700,
          color: accent ?? "var(--text-primary)",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {value}
      </div>
      <div className="text-muted" style={{ fontSize: "0.85rem", marginTop: 4 }}>
        {label}
      </div>
    </div>
  );
}
