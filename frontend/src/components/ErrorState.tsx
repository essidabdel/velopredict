import { AlertTriangle, RotateCcw } from "lucide-react";

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="card"
      style={{
        borderColor: "color-mix(in srgb, var(--status-critical) 30%, var(--border))",
        background: "color-mix(in srgb, var(--status-critical) 6%, var(--surface-1))",
        textAlign: "center",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "var(--space-2)",
      }}
    >
      <span
        className="icon-badge"
        style={{
          background: "color-mix(in srgb, var(--status-critical) 15%, transparent)",
          color: "var(--status-critical)",
        }}
      >
        <AlertTriangle size={22} />
      </span>
      <p style={{ margin: 0, fontWeight: 650 }}>Oups, un problème est survenu</p>
      <p className="text-secondary" style={{ margin: 0 }}>
        {message}
      </p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="btn btn-primary" style={{ marginTop: "var(--space-2)" }}>
          <RotateCcw size={15} />
          Réessayer
        </button>
      )}
    </div>
  );
}
