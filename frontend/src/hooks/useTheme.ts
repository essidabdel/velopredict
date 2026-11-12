import { useEffect, useState } from "react";

export type ResolvedTheme = "light" | "dark";

function resolveTheme(): ResolvedTheme {
  const attr = document.documentElement.dataset.theme;
  if (attr === "light" || attr === "dark") return attr;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

// Lecture seule : Layout.tsx reste la seule source qui écrit data-theme /
// localStorage. Utile aux composants qui doivent adapter un rendu externe
// au thème (ex. le fond de carte Leaflet), sans dépendre de leur position
// dans l'arbre React.
export function useTheme(): ResolvedTheme {
  const [theme, setTheme] = useState<ResolvedTheme>(resolveTheme);

  useEffect(() => {
    const update = () => setTheme(resolveTheme());

    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", update);

    return () => {
      observer.disconnect();
      mq.removeEventListener("change", update);
    };
  }, []);

  return theme;
}
