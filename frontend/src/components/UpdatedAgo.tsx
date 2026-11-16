import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

function label(seconds: number): string {
  if (seconds < 5) return "Mis à jour à l'instant";
  if (seconds < 60) return `Mis à jour il y a ${seconds} s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `Mis à jour il y a ${minutes} min`;
  return `Mis à jour il y a ${Math.floor(minutes / 60)} h`;
}

// Compteur vivant, indépendant du sondage : il avance chaque seconde entre
// deux rafraîchissements.
export function UpdatedAgo({ at }: { at: number | null }) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  if (at === null) return null;
  const seconds = Math.max(0, Math.round((now - at) / 1000));
  return (
    <span className="updated-ago" role="status">
      <RefreshCw size={12} aria-hidden="true" />
      {label(seconds)}
    </span>
  );
}
