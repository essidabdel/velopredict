import { Info, LayoutDashboard, MapIcon } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink, Outlet } from "react-router-dom";

const navItems: { to: string; end?: boolean; label: string; icon: ReactNode }[] = [
  { to: "/", end: true, label: "Carte", icon: <MapIcon size={16} /> },
  { to: "/dashboard", label: "Tableau de bord", icon: <LayoutDashboard size={16} /> },
  { to: "/about", label: "À propos", icon: <Info size={16} /> },
];

export function Layout() {
  return (
    <div className="app-shell">
      <header
        style={{
          borderBottom: "1px solid var(--border)",
          background: "rgba(255, 255, 255, 0.72)",
          backdropFilter: "blur(14px)",
          WebkitBackdropFilter: "blur(14px)",
          position: "sticky",
          top: 0,
          zIndex: 1000,
        }}
      >
        <nav
          style={{
            maxWidth: 1240,
            margin: "0 auto",
            padding: "var(--space-3) var(--space-5)",
            display: "flex",
            alignItems: "center",
            gap: "var(--space-4)",
            flexWrap: "wrap",
          }}
        >
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "var(--space-2)",
              marginRight: "var(--space-3)",
            }}
          >
            <span
              aria-hidden="true"
              style={{
                width: 32,
                height: 32,
                borderRadius: 9,
                background: "var(--brand-gradient)",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "var(--shadow-brand)",
                fontSize: "1.05rem",
              }}
            >
              🚲
            </span>
            <span
              className="gradient-text"
              style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "1.05rem" }}
            >
              VéloPredict
            </span>
          </span>

          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            {navItems.map(({ to, end, label, icon }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                style={({ isActive }) => ({
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 7,
                  padding: "8px 14px",
                  borderRadius: "var(--radius-full)",
                  textDecoration: "none",
                  fontSize: "0.9rem",
                  color: isActive ? "#fff" : "var(--text-secondary)",
                  fontWeight: isActive ? 650 : 500,
                  background: isActive ? "var(--brand-gradient)" : "transparent",
                  boxShadow: isActive ? "var(--shadow-brand)" : "none",
                  transition: "background 160ms, color 160ms",
                })}
              >
                {icon}
                {label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>
      <main className="app-main fade-in">
        <Outlet />
      </main>
    </div>
  );
}
