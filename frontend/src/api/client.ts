// Client HTTP minimal vers l'API FastAPI. Pas de bibliothèque de fetching
// (react-query...) : l'appli est assez petite pour s'en passer, et ça
// garde la gestion des états de chargement/erreur explicite et visible
// (voir hooks/useApi.ts).

import type {
  HistoryPoint,
  StationDetail,
  StationFilters,
  StationPrediction,
  StationSummary,
  StatsOverview,
} from "./types";

// En dev (vite dev) comme en prod (build statique servi par nginx), le
// navigateur appelle l'API directement sur son port publié par
// docker-compose. Surchargeable à la construction via VITE_API_BASE_URL.
export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function getJson<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = new URL(path, API_BASE_URL);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, value);
      }
    }
  }

  let response: Response;
  try {
    response = await fetch(url.toString());
  } catch {
    throw new ApiError("Impossible de joindre l'API VéloPredict. Vérifie qu'elle est démarrée.");
  }

  if (!response.ok) {
    // FastAPI renvoie {"detail": "..."} avec un message précis par cas
    // (ex: "historique récent insuffisant" vs "station inconnue") : on
    // l'affiche tel quel plutôt qu'un message générique par code HTTP,
    // qui masquerait la vraie raison.
    let detail: string | undefined;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail;
    } catch {
      // réponse non-JSON : on garde le message générique ci-dessous
    }
    throw new ApiError(
      detail ?? `L'API a répondu une erreur (${response.status}).`,
      response.status,
    );
  }

  return (await response.json()) as T;
}

export function fetchStations(filters: StationFilters): Promise<StationSummary[]> {
  return getJson<StationSummary[]>("/stations", {
    arrondissement: filters.arrondissement,
    velo: filters.velo,
    etat: filters.etat,
    recherche: filters.recherche,
  });
}

export function fetchStation(stationId: number): Promise<StationDetail> {
  return getJson<StationDetail>(`/stations/${stationId}`);
}

export function fetchStationHistory(stationId: number, hours = 24): Promise<HistoryPoint[]> {
  return getJson<HistoryPoint[]>(`/stations/${stationId}/history`, { hours: String(hours) });
}

export function fetchStationPrediction(stationId: number): Promise<StationPrediction> {
  return getJson<StationPrediction>(`/stations/${stationId}/prediction`);
}

export function fetchStatsOverview(): Promise<StatsOverview> {
  return getJson<StatsOverview>("/stats/overview");
}
