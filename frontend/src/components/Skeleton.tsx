export function Skeleton({
  width = "100%",
  height = 16,
  radius = "var(--radius-sm)",
  style,
}: {
  width?: string | number;
  height?: string | number;
  radius?: string;
  style?: React.CSSProperties;
}) {
  return (
    <span
      className="skeleton"
      aria-hidden="true"
      style={{ display: "block", width, height, borderRadius: radius, ...style }}
    />
  );
}

export function StatTileSkeleton() {
  return (
    <div className="card" style={{ minWidth: 160, flex: "1 1 160px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
        <Skeleton width={44} height={44} radius="var(--radius)" />
        <div style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
          <Skeleton width="60%" height={22} />
          <Skeleton width="85%" height={12} />
        </div>
      </div>
    </div>
  );
}

export function ChartCardSkeleton({ height = 220 }: { height?: number }) {
  return (
    <div className="card">
      <Skeleton width="45%" height={18} style={{ marginBottom: "var(--space-4)" }} />
      <Skeleton height={height} radius="var(--radius)" />
    </div>
  );
}
