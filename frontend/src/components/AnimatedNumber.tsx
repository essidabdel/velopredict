import { useEffect, useRef, useState } from "react";
import { formatNumber } from "../lib/format";

// Transition douce quand un chiffre change (rafraîchissement toutes les 60 s) :
// compte de l'ancienne à la nouvelle valeur. Aucune animation si l'utilisateur
// demande moins de mouvement, ni au premier affichage.
export function AnimatedNumber({ value, duration = 500 }: { value: number; duration?: number }) {
  const [shown, setShown] = useState(value);
  const fromRef = useRef(value);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const from = fromRef.current;
    if (reduce || from === value) {
      setShown(value);
      fromRef.current = value;
      return;
    }
    const start = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      setShown(Math.round(from + (value - from) * eased));
      if (progress < 1) frame = requestAnimationFrame(tick);
      else fromRef.current = value;
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, duration]);

  return <>{formatNumber(shown)}</>;
}
