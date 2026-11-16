import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HistoryPoint, StationPrediction } from "../api/types";
import { formatNumber } from "../lib/format";
import { toBikeCount } from "./PredictionPanel";

const MIN = 60_000;
const HOUR = 60 * MIN;
// Au-delà de cet écart entre deux relevés, on coupe la courbe : un trou de
// collecte ne doit pas être relié par une ligne droite qui inventerait des
// données.
const GAP_MS = 20 * MIN;

interface Row {
  t: number;
  velos: number | null;
  pred: number | null;
}

const hourFmt = new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit" });

function formatTick(t: number): string {
  return `${new Date(t).getHours()} h`;
}

// Graduations de l'axe Y : pas régulier, sans chevauchement avec la valeur
// de capacité (ex. 0, 10, 20, 30, 40, 51).
export function yTicks(capacity: number): number[] {
  const step = capacity <= 12 ? 2 : capacity <= 30 ? 5 : 10;
  const ticks: number[] = [];
  for (let v = 0; v < capacity; v += step) ticks.push(v);
  if (ticks.length > 1 && capacity - ticks[ticks.length - 1] < step * 0.6) ticks.pop();
  ticks.push(capacity);
  return ticks;
}

// Une graduation toutes les 3 h, alignée sur les heures rondes locales.
function xTicks(start: number, end: number): number[] {
  const first = new Date(start);
  first.setMinutes(0, 0, 0);
  while (first.getHours() % 3 !== 0 || first.getTime() < start) {
    first.setTime(first.getTime() + HOUR);
  }
  const ticks: number[] = [];
  for (let t = first.getTime(); t <= end; t += 3 * HOUR) ticks.push(t);
  return ticks;
}

// Retire les chutes isolées à 0 (un seul relevé à 0 entre deux relevés > 0) :
// artefacts de collecte, pas de vrais épisodes de station vide.
function dropIsolatedZeros(points: { t: number; velos: number }[]): { t: number; velos: number }[] {
  return points.filter((p, i) => {
    if (p.velos !== 0) return true;
    const prev = points[i - 1];
    const next = points[i + 1];
    return !(prev && next && prev.velos > 0 && next.velos > 0);
  });
}

// Segment reliant les deux bords d'un trou de collecte (null = séparateur).
interface Bridge {
  t: number;
  v: number | null;
}

function buildRows(
  history: HistoryPoint[],
  prediction: StationPrediction | null | undefined,
  capacity: number,
): { rows: Row[]; bridges: Bridge[]; start: number; end: number } {
  const sorted = history
    .map((p) => ({ t: new Date(p.ts).getTime(), velos: p.num_mechanical + p.num_ebike }))
    .sort((a, b) => a.t - b.t);
  const points = dropIsolatedZeros(sorted);

  const rows: Row[] = [];
  const bridges: Bridge[] = [];
  points.forEach((p, i) => {
    const prev = points[i - 1];
    if (prev && p.t - prev.t > GAP_MS) {
      rows.push({ t: prev.t + 1, velos: null, pred: null }); // coupure de l'aire
      bridges.push({ t: prev.t, v: prev.velos }, { t: p.t, v: p.velos }, { t: p.t, v: null });
    }
    rows.push({ t: p.t, velos: p.velos, pred: null });
  });

  const last = points[points.length - 1];
  const start = (points[0]?.t ?? Date.now()) as number;
  let end = last?.t ?? Date.now();

  if (prediction && last) {
    const base = new Date(prediction.as_of).getTime();
    const anchor = Number.isFinite(base) ? base : last.t;
    const lastRow = rows[rows.length - 1];
    if (lastRow) lastRow.pred = lastRow.velos; // la prévision part du dernier point réel
    rows.push({ t: anchor + 30 * MIN, velos: null, pred: toBikeCount(prediction.prediction_30min, capacity) });
    rows.push({ t: anchor + 60 * MIN, velos: null, pred: toBikeCount(prediction.prediction_60min, capacity) });
    end = anchor + 60 * MIN;
  }
  return { rows, bridges, start, end };
}

interface TipProps {
  active?: boolean;
  payload?: { payload: Row | Bridge }[];
}

function ChartTooltip({ active, payload }: TipProps) {
  // Les segments de trou portent leurs propres données : on ne garde que les lignes du graphique.
  const row = payload?.map((p) => p.payload).find((r): r is Row => "velos" in r);
  if (!active || !row) return null;
  const isReal = row.velos !== null;
  const value = isReal ? row.velos : row.pred;
  if (value === null || value === undefined) return null;
  return (
    <div className="chart-tip">
      <strong>
        {formatNumber(value)} vélo{value > 1 ? "s" : ""}
      </strong>{" "}
      · {hourFmt.format(new Date(row.t))}
      {!isReal && <div className="text-muted">Prévision</div>}
    </div>
  );
}

export function AvailabilityChart({
  history,
  capacity,
  prediction,
}: {
  history: HistoryPoint[];
  capacity: number;
  prediction?: StationPrediction | null;
}) {
  const { rows, bridges, start, end } = buildRows(history, prediction, capacity);
  const cap = Math.max(capacity, 1);

  return (
    <>
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={rows} margin={{ top: 8, right: 16, left: 4, bottom: 0 }}>
        <defs>
          <linearGradient id="availFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--series-1)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="var(--series-1)" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="var(--gridline)" vertical={false} />
        <XAxis
          dataKey="t"
          type="number"
          scale="time"
          domain={[start, end]}
          ticks={xTicks(start, end)}
          tickFormatter={formatTick}
          tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
          tickLine={false}
          axisLine={{ stroke: "var(--gridline)" }}
          allowDataOverflow
        />
        <YAxis
          domain={[0, cap]}
          ticks={yTicks(cap)}
          interval={0}
          tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
          tickLine={false}
          axisLine={{ stroke: "var(--gridline)" }}
          width={40}
          label={{
            value: "Vélos disponibles",
            angle: -90,
            position: "insideLeft",
            offset: 6,
            style: { fontSize: 12, fill: "var(--text-muted)", textAnchor: "middle" },
          }}
        />
        <ReferenceLine
          y={cap}
          stroke="var(--text-muted)"
          strokeDasharray="5 4"
          label={{
            value: `Capacité (${cap})`,
            position: "insideTopRight",
            fill: "var(--text-muted)",
            fontSize: 11,
          }}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ stroke: "var(--text-muted)", strokeDasharray: "3 3" }} />
        <Area
          type="monotone"
          dataKey="velos"
          stroke="var(--series-1)"
          strokeWidth={2}
          fill="url(#availFill)"
          connectNulls={false}
          dot={false}
          isAnimationActive={false}
        />
        {bridges.length > 0 && (
          <Line
            data={bridges}
            type="linear"
            dataKey="v"
            stroke="var(--text-muted)"
            strokeWidth={1.5}
            strokeDasharray="2 4"
            dot={false}
            activeDot={false}
            connectNulls={false}
            isAnimationActive={false}
            legendType="none"
          />
        )}
        {prediction && (
          <Line
            type="monotone"
            dataKey="pred"
            stroke="var(--brand)"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={{ r: 3, fill: "var(--brand)" }}
            connectNulls
            isAnimationActive={false}
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
    {(bridges.length > 0 || prediction) && (
      <p className="text-muted" style={{ margin: "var(--space-2) 0 0", fontSize: "0.78rem" }}>
        {bridges.length > 0 && "Pointillés gris : relevés manquants (collecte interrompue). "}
        {prediction && "Pointillés verts : prévision."}
      </p>
    )}
    </>
  );
}
