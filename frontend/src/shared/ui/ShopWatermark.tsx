import { ShopLogo } from "./ShopLogo";

export interface ShopWatermarkProps {
  name: string;
  /** Logo de la boutique ; `null` : logo générique, avec le nom dessous. */
  src: string | null;
}

/**
 * Filigrane (design-system § 6.7) : le logo, très pâle (`--opacity-watermark`), centré au fond
 * de l'écran, **derrière** le contenu (`-z-10` dans la coquille `isolate`), sans capter le
 * toucher ni être lu par les lecteurs d'écran. Les cartes, opaques, le recouvrent : le
 * contraste du texte ne change pas.
 */
export function ShopWatermark({ name, src }: ShopWatermarkProps) {
  return (
    <div
      aria-hidden="true"
      data-testid="shop-watermark"
      className="pointer-events-none fixed inset-0 -z-10 flex flex-col items-center justify-center gap-4 opacity-(--opacity-watermark) select-none"
    >
      <ShopLogo name={name} src={src} size="lg" />
      {src === null && (
        <p className="m-0 max-w-3/4 truncate text-title font-bold text-text">{name}</p>
      )}
    </div>
  );
}
