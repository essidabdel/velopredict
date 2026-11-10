import { NavLink, Outlet } from "react-router-dom";

const navLinkStyle = ({ isActive }: { isActive: boolean }): React.CSSProperties => ({
  padding: "var(--space-2) var(--space-3)",
  borderRadius: "var(--radius)",
  textDecoration: "none",
  color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
  fontWeight: isActive ? 650 : 500,
  background: isActive ? "var(--surface-2)" : "transparent",
});

export function Layout() {
  return (
    <div className="app-shell">
      <header
        style={{
          borderBottom: "1px solid var(--border)",
          background: "var(--surface-1)",
          position: "sticky",
          top: 0,
          zIndex: 1000,
        }}
      >
        <nav
          style={{
            maxWidth: 1200,
            margin: "0 auto",
            padding: "var(--space-3) var(--space-4)",
            display: "flex",
            alignItems: "center",
            gap: "var(--space-2)",
            flexWrap: "wrap",
          }}
        >
          <span style={{ fontWeight: 700, marginRight: "var(--space-4)" }}>
            🚲 VéloPredict
          </span>
          <NavLink to="/" end style={navLinkStyle}>
            Carte
          </NavLink>
          <NavLink to="/dashboard" style={navLinkStyle}>
            Tableau de bord
          </NavLink>
          <NavLink to="/about" style={navLinkStyle}>
            À propos
          </NavLink>
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
