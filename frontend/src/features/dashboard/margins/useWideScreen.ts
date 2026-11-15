import { useEffect, useState } from "react";

/** Point de rupture « ordinateur » du design system (§ 4.2) : `lg` de Tailwind, 64rem = 1024 px. */
export const WIDE_QUERY = "(min-width: 64rem)";

function matches(): boolean {
  // Sans `matchMedia` (jsdom), l'écran est traité comme un téléphone : la vue la plus sobre.
  if (typeof window.matchMedia !== "function") return false;
  return window.matchMedia(WIDE_QUERY).matches;
}

/**
 * Grand écran (≥ 1024 px) ? Suivi en direct : tableaux et graphiques ne sont chargés (import à
 * la demande) que sur grand écran, jamais sur téléphone.
 */
export function useWideScreen(): boolean {
  const [wide, setWide] = useState(matches);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    const media = window.matchMedia(WIDE_QUERY);
    const update = () => {
      setWide(media.matches);
    };
    update();
    media.addEventListener("change", update);
    return () => {
      media.removeEventListener("change", update);
    };
  }, []);
  return wide;
}
