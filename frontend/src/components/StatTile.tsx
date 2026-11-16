import type { ReactNode } from "react";
import { AnimatedNumber } from "./AnimatedNumber";

export function StatTile({
  label,
  value,
  sub,
  accent,
  icon,
}: {
  label: string;
  value: string | number;
  /** Ligne de contexte sous le libellé, ex. « 203 stations vides · 13 % ». */
  sub?: string;
  accent?: string;
  icon?: ReactNode;
}) {
  const color = accent ?? "var(--brand)";
  return (
    <div className="card card-hover stat-tile">
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
        {icon && (
          <span
            className="icon-badge"
            style={{ background: `color-mix(in srgb, ${color} 14%, transparent)`, color }}
          >
            {icon}
          </span>
        )}
        <div style={{ minWidth: 0 }}>
          <div className="stat-value">
            {typeof value === "number" ? <AnimatedNumber value={value} /> : value}
          </div>
          <div className="stat-label">{label}</div>
          {sub && <div className="stat-sub">{sub}</div>}
        </div>
      </div>
    </div>
  );
}
