import { useEffect, useState } from "react";
import type { EtatStation, StationFilters, TypeVelo } from "../api/types";
import { ETAT_LABELS } from "../constants/etat";

const inputStyle: React.CSSProperties = {
  padding: "var(--space-2) var(--space-3)",
  borderRadius: "var(--radius)",
  border: "1px solid var(--border)",
  background: "var(--surface-1)",
  minWidth: 0,
};

export function FilterBar({
  filters,
  onChange,
}: {
  filters: StationFilters;
  onChange: (next: Partial<StationFilters>) => void;
}) {
  // Champs texte : état local + debounce, pour ne pas refiltrer/réécrire
  // l'URL à chaque frappe.
  const [recherche, setRecherche] = useState(filters.recherche ?? "");
  const [arrondissement, setArrondissement] = useState(filters.arrondissement ?? "");

  useEffect(() => setRecherche(filters.recherche ?? ""), [filters.recherche]);
  useEffect(() => setArrondissement(filters.arrondissement ?? ""), [filters.arrondissement]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (recherche !== (filters.recherche ?? "")) onChange({ recherche: recherche || undefined });
    }, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recherche]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (arrondissement !== (filters.arrondissement ?? "")) {
        onChange({ arrondissement: arrondissement || undefined });
      }
    }, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [arrondissement]);

  return (
    <div
      className="card"
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "var(--space-3)",
        alignItems: "center",
      }}
    >
      <label style={{ flex: "2 1 220px", display: "flex", flexDirection: "column", gap: 4 }}>
        <span className="text-muted" style={{ fontSize: "0.8rem" }}>
          Rechercher une station
        </span>
        <input
          type="search"
          placeholder="Nom de la station…"
          value={recherche}
          onChange={(e) => setRecherche(e.target.value)}
          style={inputStyle}
        />
      </label>

      <label style={{ flex: "1 1 160px", display: "flex", flexDirection: "column", gap: 4 }}>
        <span className="text-muted" style={{ fontSize: "0.8rem" }}>
          Commune / arrondissement
        </span>
        <input
          type="text"
          placeholder="ex: 16e, Pantin…"
          value={arrondissement}
          onChange={(e) => setArrondissement(e.target.value)}
          style={inputStyle}
        />
      </label>

      <label style={{ flex: "1 1 140px", display: "flex", flexDirection: "column", gap: 4 }}>
        <span className="text-muted" style={{ fontSize: "0.8rem" }}>
          Type de vélo
        </span>
        <select
          value={filters.velo ?? ""}
          onChange={(e) => onChange({ velo: (e.target.value || undefined) as TypeVelo | undefined })}
          style={inputStyle}
        >
          <option value="">Tous</option>
          <option value="mecanique">Mécanique</option>
          <option value="electrique">Électrique</option>
        </select>
      </label>

      <label style={{ flex: "1 1 140px", display: "flex", flexDirection: "column", gap: 4 }}>
        <span className="text-muted" style={{ fontSize: "0.8rem" }}>
          État
        </span>
        <select
          value={filters.etat ?? ""}
          onChange={(e) =>
            onChange({ etat: (e.target.value || undefined) as EtatStation | undefined })
          }
          style={inputStyle}
        >
          <option value="">Tous</option>
          <option value="vide">{ETAT_LABELS.vide}</option>
          <option value="faible">{ETAT_LABELS.faible}</option>
          <option value="disponible">{ETAT_LABELS.disponible}</option>
          <option value="pleine">{ETAT_LABELS.pleine}</option>
        </select>
      </label>

      {(filters.recherche || filters.arrondissement || filters.velo || filters.etat) && (
        <button
          type="button"
          onClick={() => {
            setRecherche("");
            setArrondissement("");
            onChange({ recherche: undefined, arrondissement: undefined, velo: undefined, etat: undefined });
          }}
          style={{
            ...inputStyle,
            cursor: "pointer",
            background: "var(--surface-2)",
            alignSelf: "flex-end",
          }}
        >
          Réinitialiser
        </button>
      )}
    </div>
  );
}
