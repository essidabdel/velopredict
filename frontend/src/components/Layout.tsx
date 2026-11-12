import { Bike, Info, LayoutDashboard, MapIcon, Menu, Moon, Sun, X } from "lucide-react";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { NavLink, Outlet } from "react-router-dom";

type Theme = "light" | "dark";

const THEME_KEY = "velopredict:theme";

function getInitialTheme(): Theme {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    // localStorage indisponible (navigation privée stricte...) : on retombe
    // sur la préférence système.
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

const navItems: { to: string; end?: boolean; label: string; icon: ReactNode }[] = [
  { to: "/", end: true, label: "Carte", icon: <MapIcon size={16} /> },
  { to: "/dashboard", label: "Tableau de bord", icon: <LayoutDashboard size={16} /> },
  { to: "/about", label: "À propos", icon: <Info size={16} /> },
];

const navLinkStyle = ({ isActive }: { isActive: boolean }): React.CSSProperties => ({
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
});

const mobileNavLinkStyle = ({ isActive }: { isActive: boolean }): React.CSSProperties => ({
  display: "flex",
  alignItems: "center",
  gap: 10,
  padding: "12px 14px",
  borderRadius: "var(--radius)",
  textDecoration: "none",
  fontSize: "1rem",
  color: isActive ? "#fff" : "var(--text-primary)",
  fontWeight: isActive ? 650 : 500,
  background: isActive ? "var(--brand-gradient)" : "var(--surface-2)",
});

export function Layout() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      // Pas grave : le choix ne sera simplement pas mémorisé.
    }
  }, [theme]);

  // Ferme le panneau mobile si l'écran repasse en largeur desktop.
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 761px)");
    const onChange = () => setMenuOpen(false);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return (
    <div className="app-shell">
      <a href="#contenu-principal" className="skip-link">
        Aller au contenu principal
      </a>
      <header
        style={{
          borderBottom: "1px solid var(--border)",
          background: "color-mix(in srgb, var(--surface-1) 72%, transparent)",
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
            justifyContent: "space-between",
            gap: "var(--space-4)",
          }}
        >
          <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-2)" }}>
            <span
              aria-hidden="true"
              style={{
                width: 32,
                height: 32,
                borderRadius: 9,
                background: "var(--brand)",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#fff",
              }}
            >
              <Bike size={17} />
            </span>
            <span
              style={{
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: "1.05rem",
                color: "var(--text-primary)",
              }}
            >
              VéloPredict
            </span>
          </span>

          <div className="nav-links">
            {navItems.map(({ to, end, label, icon }) => (
              <NavLink key={to} to={to} end={end} style={navLinkStyle}>
                {icon}
                {label}
              </NavLink>
            ))}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <button
              type="button"
              className="icon-toggle"
              onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
              aria-label={theme === "dark" ? "Passer au thème clair" : "Passer au thème sombre"}
              title={theme === "dark" ? "Thème clair" : "Thème sombre"}
            >
              {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            <button
              type="button"
              className="icon-toggle nav-toggle-btn"
              onClick={() => setMenuOpen(true)}
              aria-label="Ouvrir le menu"
              aria-expanded={menuOpen}
            >
              <Menu size={18} />
            </button>
          </div>
        </nav>
      </header>

      {menuOpen && (
        <>
          <button
            type="button"
            className="nav-scrim"
            aria-label="Fermer le menu"
            onClick={() => setMenuOpen(false)}
            style={{ border: "none", padding: 0, cursor: "pointer" }}
          />
          <div className="nav-panel-mobile" role="dialog" aria-label="Menu de navigation">
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button
                type="button"
                className="icon-toggle"
                onClick={() => setMenuOpen(false)}
                aria-label="Fermer le menu"
                style={{ background: "var(--surface-3)" }}
              >
                <X size={18} />
              </button>
            </div>
            {navItems.map(({ to, end, label, icon }) => (
              <NavLink key={to} to={to} end={end} style={mobileNavLinkStyle} onClick={() => setMenuOpen(false)}>
                {icon}
                {label}
              </NavLink>
            ))}
          </div>
        </>
      )}

      <main id="contenu-principal" className="app-main fade-in">
        <Outlet />
      </main>
    </div>
  );
}
