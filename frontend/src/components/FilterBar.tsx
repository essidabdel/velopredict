import { Bike, MapPin, RotateCcw, Search, SlidersHorizontal, X } from "lucide-react";
import { useEffect, useState } from "react";
import type { EtatStation, StationFilters, TypeVelo } from "../api/types";
import { ETAT_LABELS } from "../constants/etat";

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

  const hasActiveFilters = Boolean(
    filters.recherche || filters.arrondissement || filters.velo || filters.etat,
  );

  return (
    <div className="search-toolbar">
      <div className="search-hero">
        <Search size={19} />
        <input
          type="search"
          placeholder="Chercher une station par nom…"
          value={recherche}
          onChange={(e) => setRecherche(e.target.value)}
          aria-label="Rechercher une station"
        />
        {recherche && (
          <button
            type="button"
            className="search-hero-clear"
            onClick={() => setRecherche("")}
            aria-label="Effacer la recherche"
          >
            <X size={15} />
          </button>
        )}
      </div>

      <div className="filter-row">
        <label className="field" style={{ flex: "1 1 170px" }}>
          <span className="field-label">Commune / arrondissement</span>
          <div className="input-wrap">
            <MapPin />
            <input
              type="text"
              placeholder="ex : 16e, Pantin…"
              value={arrondissement}
              onChange={(e) => setArrondissement(e.target.value)}
              className="input"
            />
          </div>
        </label>

        <label className="field" style={{ flex: "1 1 150px" }}>
          <span className="field-label">Type de vélo</span>
          <div className="input-wrap">
            <Bike />
            <select
              value={filters.velo ?? ""}
              onChange={(e) => onChange({ velo: (e.target.value || undefined) as TypeVelo | undefined })}
              className="input"
            >
              <option value="">Tous</option>
              <option value="mecanique">Mécanique</option>
              <option value="electrique">Électrique</option>
            </select>
          </div>
        </label>

        <label className="field" style={{ flex: "1 1 150px" }}>
          <span className="field-label">État</span>
          <div className="input-wrap">
            <SlidersHorizontal />
            <select
              value={filters.etat ?? ""}
              onChange={(e) =>
                onChange({ etat: (e.target.value || undefined) as EtatStation | undefined })
              }
              className="input"
            >
              <option value="">Tous</option>
              <option value="vide">{ETAT_LABELS.vide}</option>
              <option value="faible">{ETAT_LABELS.faible}</option>
              <option value="disponible">{ETAT_LABELS.disponible}</option>
              <option value="pleine">{ETAT_LABELS.pleine}</option>
            </select>
          </div>
        </label>

        {hasActiveFilters && (
          <button
            type="button"
            onClick={() => {
              setRecherche("");
              setArrondissement("");
              onChange({ recherche: undefined, arrondissement: undefined, velo: undefined, etat: undefined });
            }}
            className="btn btn-secondary"
            style={{ alignSelf: "flex-end" }}
          >
            <RotateCcw size={15} />
            Réinitialiser
          </button>
        )}
      </div>
    </div>
  );
}
