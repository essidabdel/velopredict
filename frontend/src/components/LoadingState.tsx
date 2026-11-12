import { Loader2 } from "lucide-react";

export function LoadingState({ label = "Chargement…" }: { label?: string }) {
  return (
    <div
      role="status"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "var(--space-3)",
        padding: "var(--space-7) var(--space-5)",
        color: "var(--text-muted)",
      }}
    >
      <Loader2 className="spinner" size={28} color="var(--brand)" />
      <span>{label}</span>
    </div>
  );
}
