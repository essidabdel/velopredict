import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { StationSummary, StatsOverview } from "../api/types";
import { ETAT_COLORS, ETAT_LABELS, ETAT_ORDER } from "../constants/etat";

const tooltipStyle = {
  background: "var(--surface-1)",
  border: "1px solid var(--border)",
  borderRadius: 10,
  fontSize: 13,
  boxShadow: "var(--shadow-md)",
};

const axisTick = { fontSize: 11, fill: "var(--text-muted)" };
const axisLine = { stroke: "var(--gridline)" };

// Barre de composition (vide/faible/disponible/pleine) : une seule barre
// segmentée proportionnellement, plutôt que 4 barres verticales séparées
// — se lit en un coup d'œil comme "l'état du réseau maintenant", le
// langage visuel typique d'un tableau de bord (vs. un graphique d'analyse).
export function StatusCompositionBar({ stations }: { stations: StationSummary[] }) {
  const total = stations.length || 1;
  const segments = ETAT_ORDER.filter((etat) => etat !== "inconnue").map((etat) => {
    const count = stations.filter((s) => s.etat === etat).length;
    return { etat, count, pct: (count / total) * 100 };
  });

  return (
    <div>
      <div
        style={{
          display: "flex",
          height: 20,
          borderRadius: "var(--radius-full)",
          overflow: "hidden",
          background: "var(--surface-2)",
        }}
      >
        {segments.map((seg) =>
          seg.pct > 0 ? (
            <div
              key={seg.etat}
              title={`${ETAT_LABELS[seg.etat]} : ${seg.count}`}
              style={{
                width: `${seg.pct}%`,
                background: ETAT_COLORS[seg.etat],
                marginRight: 2,
              }}
            />
          ) : null,
        )}
      </div>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "var(--space-4)",
          marginTop: "var(--space-4)",
        }}
      >
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
            <span
              style={{
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: "1.1rem",
                color: "var(--text-primary)",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {seg.count}
            </span>
            <span className="text-muted" style={{ fontSize: "0.82rem" }}>
              {ETAT_LABELS[seg.etat]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function BikeTypeChart({ stats }: { stats: StatsOverview }) {
  const data = [
    { type: "Mécaniques", count: stats.total_mechanical, color: "var(--series-1)" },
    { type: "Électriques", count: stats.total_ebike, color: "var(--series-2)" },
  ];

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 8, right: 24, left: 8, bottom: 0 }}
        barCategoryGap="35%"
      >
        <XAxis type="number" tick={axisTick} tickLine={false} axisLine={axisLine} allowDecimals={false} />
        <YAxis
          type="category"
          dataKey="type"
          tick={axisTick}
          tickLine={false}
          axisLine={axisLine}
          width={80}
        />
        <Tooltip contentStyle={tooltipStyle} formatter={(value) => [`${value} vélos`, ""]} />
        <Bar dataKey="count" radius={[0, 6, 6, 0]} maxBarSize={28}>
          {data.map((entry) => (
            <Cell key={entry.type} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function TopCommunesVidesChart({ stations }: { stations: StationSummary[] }) {
  const counts = new Map<string, number>();
  for (const station of stations) {
    if (station.etat !== "vide" || !station.commune_nom) continue;
    counts.set(station.commune_nom, (counts.get(station.commune_nom) ?? 0) + 1);
  }
  const data = [...counts.entries()]
    .map(([commune, count]) => ({ commune, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8)
    .reverse();

  if (data.length === 0) {
    return <p className="text-muted">Aucune station vide en ce moment.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, left: 8, bottom: 0 }}>
        <XAxis type="number" tick={axisTick} tickLine={false} axisLine={axisLine} allowDecimals={false} />
        <YAxis
          type="category"
          dataKey="commune"
          tick={axisTick}
          tickLine={false}
          axisLine={axisLine}
          width={120}
        />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(value) => [`${value} station(s) vide(s)`, ""]}
        />
        <Bar dataKey="count" radius={[0, 6, 6, 0]} maxBarSize={16} fill={ETAT_COLORS.vide} />
      </BarChart>
    </ResponsiveContainer>
  );
}
