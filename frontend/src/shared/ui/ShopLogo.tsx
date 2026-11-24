import { useState } from "react";
import { requireText } from "./controlClasses";
import { initialsOf } from "./initials";

export type ShopLogoSize = "sm" | "md" | "lg";

export interface ShopLogoProps {
  /** Nom de la boutique : initiales du logo générique. */
  name: string;
  /** Adresse de l'image (lien signé ou aperçu local) ; `null` : logo générique. */
  src: string | null;
  size?: ShopLogoSize;
  /** Texte alternatif ; vide (défaut) : logo décoratif, le nom est écrit à côté. */
  alt?: string;
}

const BOX: Record<ShopLogoSize, string> = {
  sm: "size-(--logo-sm) rounded-sm text-body",
  md: "size-(--logo-md) rounded-md text-title",
  lg: "size-(--logo-lg) rounded-lg text-kpi",
};

/**
 * Logo de la boutique (design-system § 6.7) : l'image envoyée par le gérant, carré arrondi ;
 * sans image (ou image illisible, lien expiré) : **logo générique**, badge `primary` aux
 * initiales du nom. Jamais vide, jamais d'image cassée.
 */
export function ShopLogo({ name, src, size = "sm", alt = "" }: ShopLogoProps) {
  requireText("ShopLogo", "name", name);
  const [broken, setBroken] = useState<string | null>(null);
  const box = `${BOX[size]} shrink-0`;
  if (src !== null && broken !== src) {
    return (
      <img
        src={src}
        alt={alt}
        className={`${box} bg-surface object-contain`}
        onError={() => {
          setBroken(src);
        }}
      />
    );
  }
  return (
    <span
      {...(alt === "" ? { "aria-hidden": true } : { role: "img", "aria-label": alt })}
      className={`${box} inline-flex items-center justify-center bg-primary font-bold text-on-primary select-none`}
    >
      {initialsOf(name)}
    </span>
  );
}
