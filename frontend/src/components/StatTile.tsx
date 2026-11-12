import type { ReactNode } from "react";

export function StatTile({
  label,
  value,
  accent,
  icon,
}: {
  label: string;
  value: string | number;
  accent?: string;
  icon?: ReactNode;
}) {
  const color = accent ?? "var(--brand)";
  return (
    <div className="card card-hover" style={{ minWidth: 160, flex: "1 1 160px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
        {icon && (
          <span
            className="icon-badge"
            style={{ background: `color-mix(in srgb, ${color} 14%, transparent)`, color }}
          >
            {icon}
          </span>
        )}
        <div>
          <div
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "1.7rem",
              fontWeight: 700,
              lineHeight: 1.1,
              color: "var(--text-primary)",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {value}
          </div>
          <div className="text-muted" style={{ fontSize: "0.82rem", marginTop: 2 }}>
            {label}
          </div>
        </div>
      </div>
    </div>
  );
}
