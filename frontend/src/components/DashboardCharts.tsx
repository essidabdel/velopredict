import { useState } from "react";
import { Bar, BarChart, Cell, LabelList, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { StationSummary, StatsOverview } from "../api/types";
import { ETAT_COLORS, ETAT_LABELS, ETAT_ORDER } from "../constants/etat";
import { formatNumber, formatPercent, shortCommune } from "../lib/format";

const tooltipStyle = {
  background: "var(--surface-1)",
  border: "1px solid var(--border)",
  borderRadius: 10,
  fontSize: 13,
  boxShadow: "var(--shadow-md)",
};

const axisTick = { fontSize: 12, fill: "var(--text-secondary)" };
const axisLine = { stroke: "var(--gridline)" };

// Barre de composition (vide / presque vide / disponible / pleine) : une seule
// barre segmentée proportionnellement, qui se lit en un coup d'œil comme
// « l'état du réseau maintenant ». Le pourcentage est inscrit dans chaque
// segment assez large ; au survol, une infobulle donne le détail.
export function StatusCompositionBar({ stations }: { stations: StationSummary[] }) {
  const [hovered, setHovered] = useState<string | null>(null);
  const total = stations.length || 1;
  const segments = ETAT_ORDER.filter((etat) => etat !== "inconnue").map((etat) => {
    const count = stations.filter((s) => s.etat === etat).length;
    return { etat, count, pct: (count / total) * 100 };
  });

  return (
    <div>
      <div className="status-bar" role="img" aria-label="Répartition des stations par état">
        {segments.map((seg) =>
          seg.pct > 0 ? (
            <div
              key={seg.etat}
              className="status-seg"
              onMouseEnter={() => setHovered(seg.etat)}
              onMouseLeave={() => setHovered(null)}
              style={{ width: `${seg.pct}%`, background: ETAT_COLORS[seg.etat] }}
            >
              {seg.pct >= 7 && (
                <span style={{ color: seg.etat === "faible" ? "#2a1800" : "#fff" }}>
                  {formatPercent(seg.count, total)}
                </span>
              )}
              {hovered === seg.etat && (
                <span className="status-tip" role="tooltip">
                  <strong>{ETAT_LABELS[seg.etat]}</strong>
                  <br />
                  {formatNumber(seg.count)} stations · {formatPercent(seg.count, total)}
                </span>
              )}
            </div>
          ) : null,
        )}
      </div>
      <div className="status-legend">
        {segments.map((seg) => (
          <div key={seg.etat} style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
            <span
              aria-hidden="true"
              style={{
                width: 9,
                height: 9,
                borderRadius: "50%",
                background: ETAT_COLORS[seg.etat],
                display: "inline-block",
              }}
            />
            <span className="legend-value">{formatNumber(seg.count)}</span>
            <span className="text-muted" style={{ fontSize: "0.85rem" }}>
              {ETAT_LABELS[seg.etat]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Donut mécaniques / électriques : total au centre, valeurs et pourcentages
// en légende (plus lisible que deux barres dont une écrase l'autre).
export function BikeTypeChart({ stats }: { stats: StatsOverview }) {
  const data = [
    { type: "Mécaniques", count: stats.total_mechanical, color: "var(--series-1)" },
    { type: "Électriques", count: stats.total_ebike, color: "var(--series-2)" },
  ];
  const total = stats.total_mechanical + stats.total_ebike;

  return (
    <div className="donut-wrap">
      <div className="donut-chart">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="count"
              nameKey="type"
              innerRadius="64%"
              outerRadius="92%"
              paddingAngle={2}
              stroke="var(--surface-1)"
              strokeWidth={2}
              isAnimationActive={false}
            >
              {data.map((entry) => (
                <Cell key={entry.type} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value, name) => [`${formatNumber(Number(value))} vélos`, String(name)]}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-center">
          <span className="donut-total">{formatNumber(total)}</span>
          <span className="text-muted" style={{ fontSize: "0.78rem" }}>
            vélos
          </span>
        </div>
      </div>
      <ul className="donut-legend">
        {data.map((entry) => (
          <li key={entry.type}>
            <span aria-hidden="true" className="legend-dot" style={{ background: entry.color }} />
            <span>
              <span className="legend-value">{formatNumber(entry.count)}</span>{" "}
              <span className="text-secondary">
                {entry.type} · {formatPercent(entry.count, total)}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// Top 8 des communes ayant le plus de stations vides, la pire en haut,
// valeur au bout de chaque barre.
export function TopCommunesVidesChart({ stations }: { stations: StationSummary[] }) {
  const counts = new Map<string, number>();
  for (const station of stations) {
    if (station.etat !== "vide" || !station.commune_nom) continue;
    const commune = shortCommune(station.commune_nom);
    counts.set(commune, (counts.get(commune) ?? 0) + 1);
  }
  const data = [...counts.entries()]
    .map(([commune, count]) => ({ commune, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  if (data.length === 0) {
    return <p className="text-muted">Aucune station vide en ce moment.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={data.length * 34 + 16}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 36, left: 0, bottom: 0 }}>
        <XAxis type="number" hide domain={[0, "dataMax"]} />
        <YAxis
          type="category"
          dataKey="commune"
          tick={axisTick}
          tickLine={false}
          axisLine={axisLine}
          width={110}
          interval={0}
        />
        <Tooltip
          cursor={{ fill: "var(--surface-2)" }}
          contentStyle={tooltipStyle}
          formatter={(value) => [`${formatNumber(Number(value))} stations vides`, ""]}
        />
        <Bar dataKey="count" radius={[0, 6, 6, 0]} maxBarSize={18} fill={ETAT_COLORS.vide} isAnimationActive={false}>
          <LabelList
            dataKey="count"
            position="right"
            style={{ fill: "var(--text-primary)", fontSize: 12, fontWeight: 700 }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
