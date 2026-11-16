// Formatage à la française, partagé par toutes les pages.

const nf = new Intl.NumberFormat("fr-FR");
const pf = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });

/** 18289 → « 18 289 » (espace insécable fine, comme le veut fr-FR). */
export function formatNumber(value: number): string {
  return nf.format(value);
}

/** Part en pourcentage entier : (203, 1522) → « 13 % ». */
export function formatPercent(part: number, total: number): string {
  if (total <= 0) return "0 %";
  return `${pf.format((part / total) * 100)} %`;
}

/** « Paris 15e Arrondissement » → « Paris 15e ». Les autres communes sont inchangées. */
export function shortCommune(name: string | null | undefined): string {
  if (!name) return "Commune inconnue";
  return name.replace(/\s+arrondissement$/i, "").trim();
}

/** « vélo » / « vélos » selon la quantité (0 et 1 au singulier). */
export function pluralVelos(n: number): string {
  return Math.abs(n) > 1 ? "vélos" : "vélo";
}
