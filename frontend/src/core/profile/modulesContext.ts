import { createContext, useContext } from "react";
import type { ShopModules } from "./modules";

/** Modules actifs de la boutique ouverte, fournis par la coquille (`ShopShell`). */
export const ModulesContext = createContext<ShopModules | null>(null);

/**
 * Point d'accès **unique** aux modules de la boutique active : chaque point d'entrée d'un module
 * (menu, tuile, bouton, section, lien) se montre seulement si `useModules().has(module)`.
 * Hors d'une boutique, c'est une erreur de câblage (fail-fast).
 */
export function useModules(): ShopModules {
  const modules = useContext(ModulesContext);
  if (modules === null) throw new Error("useModules doit être appelé sous la coquille d'une boutique");
  return modules;
}
