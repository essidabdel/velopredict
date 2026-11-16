// Vocabulaire visuel partagé (carte, légende, filtres, fiche station).
// Couleurs issues de la palette de référence du skill dataviz : "vide"/
// "faible"/"disponible" réutilisent le statut (critical/warning/good,
// jamais pour une série catégorielle) ; "pleine" n'est pas un échec de
// disponibilité pour quelqu'un qui loue un vélo (juste plus de place pour
// le déposer), donc identité catégorielle (bleu, slot 1) plutôt que statut.
import type { EtatStation, NiveauRisque } from "../api/types";

// Les valeurs techniques de l'API ("faible"…) ne changent pas : seul le
// libellé affiché est harmonisé partout (carte, légende, filtres, fiche).
export const ETAT_LABELS: Record<EtatStation, string> = {
  vide: "Vide",
  faible: "Presque vide",
  disponible: "Disponible",
  pleine: "Pleine",
  inconnue: "Inconnu",
};

export const ETAT_COLORS: Record<EtatStation, string> = {
  vide: "#d03b3b",
  faible: "#fab219",
  disponible: "#0ca30c",
  pleine: "#2a78d6",
  inconnue: "#898781",
};

export const ETAT_ORDER: EtatStation[] = ["vide", "faible", "disponible", "pleine", "inconnue"];

// Explication en langage courant, affichée sur la fiche station.
export const ETAT_EXPLICATIONS: Record<EtatStation, string> = {
  vide: "Aucun vélo à emprunter pour le moment.",
  faible: "Il en reste peu (20 % de la capacité ou moins), mieux vaut venir vite.",
  disponible: "Des vélos à emprunter et des bornes libres.",
  pleine: "Plus de borne libre pour déposer un vélo.",
  inconnue: "Pas d'information fiable pour l'instant.",
};

export const NIVEAU_RISQUE_LABELS: Record<NiveauRisque, string> = {
  eleve: "Élevé",
  moyen: "Moyen",
  faible: "Faible",
};

export const NIVEAU_RISQUE_COLORS: Record<NiveauRisque, string> = {
  eleve: "#d03b3b",
  moyen: "#fab219",
  faible: "#0ca30c",
};
