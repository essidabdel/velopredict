export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="card"
      style={{
        borderColor: "var(--status-critical)",
        background: "#fdf1f0",
        color: "var(--text-primary)",
        textAlign: "center",
      }}
    >
      <p style={{ margin: 0, fontWeight: 600 }}>Oups, un problème est survenu</p>
      <p className="text-secondary" style={{ margin: "var(--space-2) 0 0" }}>
        {message}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          style={{
            marginTop: "var(--space-3)",
            padding: "var(--space-2) var(--space-4)",
            borderRadius: "var(--radius)",
            border: "1px solid var(--border)",
            background: "var(--surface-1)",
            cursor: "pointer",
          }}
        >
          Réessayer
        </button>
      )}
    </div>
  );
}
