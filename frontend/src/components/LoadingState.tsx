export function LoadingState({ label = "Chargement…" }: { label?: string }) {
  return (
    <div role="status" style={{ padding: "var(--space-5)", textAlign: "center" }}>
      <span className="text-muted">{label}</span>
    </div>
  );
}
