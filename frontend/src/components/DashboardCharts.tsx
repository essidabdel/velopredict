import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { StationSummary, StatsOverview } from "../api/types";
import { ETAT_COLORS, ETAT_LABELS, ETAT_ORDER } from "../constants/etat";

const tooltipStyle = {
  background: "var(--surface-1)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 13,
};

const axisTick = { fontSize: 11, fill: "var(--text-muted)" };
const axisLine = { stroke: "var(--gridline)" };

export function EtatBreakdownChart({ stations }: { stations: StationSummary[] }) {
  const data = ETAT_ORDER.filter((etat) => etat !== "inconnue").map((etat) => ({
    etat,
    label: ETAT_LABELS[etat],
    count: stations.filter((s) => s.etat === etat).length,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }} barCategoryGap="30%">
        <XAxis dataKey="label" tick={axisTick} tickLine={false} axisLine={axisLine} />
        <YAxis tick={axisTick} tickLine={false} axisLine={axisLine} width={32} allowDecimals={false} />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(value) => [`${value} stations`, ""]}
        />
        <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={56}>
          {data.map((entry) => (
            <Cell key={entry.etat} fill={ETAT_COLORS[entry.etat]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
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
        <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={32}>
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
        <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={18} fill={ETAT_COLORS.vide} />
      </BarChart>
    </ResponsiveContainer>
  );
}
