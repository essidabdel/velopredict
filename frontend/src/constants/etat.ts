// Vocabulaire visuel partagé (carte, légende, filtres, fiche station).
// Couleurs issues de la palette de référence du skill dataviz : "vide"/
// "faible"/"disponible" réutilisent le statut (critical/warning/good,
// jamais pour une série catégorielle) ; "pleine" n'est pas un échec de
// disponibilité pour quelqu'un qui loue un vélo (juste plus de place pour
// le déposer), donc identité catégorielle (bleu, slot 1) plutôt que statut.
import type { EtatStation } from "../api/types";

export const ETAT_LABELS: Record<EtatStation, string> = {
  vide: "Vide",
  faible: "Disponibilité faible",
  disponible: "Disponible",
  pleine: "Pleine",
  inconnue: "État inconnu",
};

export const ETAT_COLORS: Record<EtatStation, string> = {
  vide: "#d03b3b",
  faible: "#fab219",
  disponible: "#0ca30c",
  pleine: "#2a78d6",
  inconnue: "#898781",
};

export const ETAT_ORDER: EtatStation[] = ["vide", "faible", "disponible", "pleine", "inconnue"];

export const NIVEAU_RISQUE_LABELS: Record<"eleve" | "moyen" | "faible", string> = {
  eleve: "Élevé",
  moyen: "Moyen",
  faible: "Faible",
};

export const NIVEAU_RISQUE_COLORS: Record<"eleve" | "moyen" | "faible", string> = {
  eleve: "#d03b3b",
  moyen: "#fab219",
  faible: "#0ca30c",
};
