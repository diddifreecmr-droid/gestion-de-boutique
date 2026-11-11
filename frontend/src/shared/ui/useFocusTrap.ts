import { useEffect, useRef, type KeyboardEvent, type RefObject } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Éléments focalisables d'un conteneur, dans l'ordre du document. */
export function focusableIn(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (element) => !element.hidden,
  );
}

/**
 * Piège le focus dans `container` tant que `active` : focus initial sur l'élément `initialId` (ou le
 * premier élément), Tab / Maj+Tab bouclent, Échap appelle `onEscape`. À la fermeture, le
 * focus revient sur l'élément qui l'avait avant l'ouverture (WAI-ARIA « dialog modal »).
 */
export function useFocusTrap(
  container: RefObject<HTMLElement | null>,
  active: boolean,
  onEscape: () => void,
  initialId?: string,
) {
  const escapeRef = useRef(onEscape);
  useEffect(() => {
    escapeRef.current = onEscape;
  });

  useEffect(() => {
    if (!active) return;
    const root = container.current;
    if (root === null)
      throw new Error("useFocusTrap : conteneur absent alors que le piège est actif");
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const initial = initialId === undefined ? null : document.getElementById(initialId);
    (initial ?? focusableIn(root)[0] ?? root).focus();
    return () => {
      previous?.focus();
    };
  }, [active, container, initialId]);

  return (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      escapeRef.current();
      return;
    }
    const root = container.current;
    if (event.key !== "Tab" || root === null) return;
    const items = focusableIn(root);
    const first = items[0];
    const last = items.at(-1);
    if (first === undefined || last === undefined) {
      event.preventDefault();
      return;
    }
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };
}
