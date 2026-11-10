import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { HistoryPoint } from "../api/types";

function formatHeure(iso: string): string {
  return new Date(iso).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

export function AvailabilityChart({
  history,
  capacity,
}: {
  history: HistoryPoint[];
  capacity: number;
}) {
  const data = history.map((point) => ({
    heure: formatHeure(point.ts),
    velos: point.num_mechanical + point.num_ebike,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--gridline)" vertical={false} />
        <XAxis
          dataKey="heure"
          tick={{ fontSize: 11, fill: "var(--text-muted)" }}
          interval="preserveStartEnd"
          tickLine={false}
          axisLine={{ stroke: "var(--gridline)" }}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "var(--text-muted)" }}
          domain={[0, Math.max(capacity, 1)]}
          tickLine={false}
          axisLine={{ stroke: "var(--gridline)" }}
          width={32}
        />
        <Tooltip
          contentStyle={{
            background: "var(--surface-1)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 13,
          }}
          labelStyle={{ color: "var(--text-secondary)" }}
          formatter={(value) => [`${value} vélos`, "Disponibles"]}
        />
        <Line
          type="monotone"
          dataKey="velos"
          stroke="var(--series-1)"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
