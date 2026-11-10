// Synchronise les filtres de la carte avec l'URL (partage/retour en
// arrière possible), via react-router.
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import type { EtatStation, StationFilters, TypeVelo } from "../api/types";

export function useUrlFilters(): {
  filters: StationFilters;
  setFilters: (next: Partial<StationFilters>) => void;
} {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters: StationFilters = useMemo(
    () => ({
      arrondissement: searchParams.get("arrondissement") ?? undefined,
      velo: (searchParams.get("velo") as TypeVelo | null) ?? undefined,
      etat: (searchParams.get("etat") as EtatStation | null) ?? undefined,
      recherche: searchParams.get("q") ?? undefined,
    }),
    [searchParams],
  );

  function setFilters(next: Partial<StationFilters>) {
    const merged = { ...filters, ...next };
    const params = new URLSearchParams();
    if (merged.arrondissement) params.set("arrondissement", merged.arrondissement);
    if (merged.velo) params.set("velo", merged.velo);
    if (merged.etat) params.set("etat", merged.etat);
    if (merged.recherche) params.set("q", merged.recherche);
    setSearchParams(params, { replace: true });
  }

  return { filters, setFilters };
}
