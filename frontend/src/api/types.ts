// Types alignés sur api/schemas.py (FastAPI). Garder synchronisé
// manuellement : pas de génération automatique dans ce projet.

export type EtatStation = "vide" | "faible" | "pleine" | "disponible" | "inconnue";
export type TypeVelo = "mecanique" | "electrique";
export type NiveauRisque = "eleve" | "moyen" | "faible";

export interface StationSummary {
  station_id: number;
  name: string;
  commune_code: string | null;
  commune_nom: string | null;
  lat: number;
  lon: number;
  capacity: number;
  etat: EtatStation;
  num_mechanical: number | null;
  num_ebike: number | null;
  num_docks_available: number | null;
  is_renting: boolean | null;
  is_returning: boolean | null;
  last_reported: number | null;
}

export interface StationDetail extends StationSummary {
  collected_at: string | null;
}

export interface HistoryPoint {
  ts: string;
  num_mechanical: number;
  num_ebike: number;
  num_docks_available: number;
  is_renting: boolean;
  is_returning: boolean;
}

export interface StationPrediction {
  station_id: number;
  as_of: string;
  bikes_now: number;
  prediction_30min: number;
  prediction_60min: number;
  risk_level_30min: NiveauRisque;
}

export interface StatsOverview {
  nb_stations: number;
  nb_stations_avec_etat: number;
  total_bikes_available: number;
  total_mechanical: number;
  total_ebike: number;
  total_docks_available: number;
  nb_stations_vides: number;
  nb_stations_pleines: number;
}

export interface StationFilters {
  arrondissement?: string;
  velo?: TypeVelo;
  etat?: EtatStation;
  recherche?: string;
}
