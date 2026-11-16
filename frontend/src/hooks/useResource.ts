// Chargement de données minimal : états loading/error explicites,
// rafraîchissement en tâche de fond optionnel (sondage), sans écraser les
// données déjà affichées pendant un refresh (évite un clignotement de
// l'UI toutes les 60s).
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";

interface UseResourceOptions {
  pollMs?: number;
}

export interface ResourceState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  /** Horodatage (ms) du dernier chargement réussi, pour « mis à jour il y a X s ». */
  updatedAt: number | null;
  reload: () => void;
}

export function useResource<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: UseResourceOptions = {},
): ResourceState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const load = useCallback(async (background: boolean) => {
    if (!background) setLoading(true);
    try {
      const result = await fetcherRef.current();
      setData(result);
      setError(null);
      setUpdatedAt(Date.now());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur inattendue.");
    } finally {
      if (!background) setLoading(false);
    }
    // key encode tous les paramètres pertinents : on resynchronise dessus.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    setLoading(true);
    void load(false);
    if (!options.pollMs) return;
    const interval = setInterval(() => void load(true), options.pollMs);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load, options.pollMs]);

  return { data, loading, error, updatedAt, reload: () => void load(false) };
}
