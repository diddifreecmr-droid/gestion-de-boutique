/**
 * Mesures de mise en page dans le navigateur (recette A11Y-02, A11Y-06).
 */
import type { Page } from "@playwright/test";

export const MIN_TOUCH_PX = 48;
export const MIN_GAP_PX = 8;

export interface PageWidth {
  scrollWidth: number;
  clientWidth: number;
}

/** Largeur défilable du document comparée à la largeur visible. */
export async function pageWidth(page: Page): Promise<PageWidth> {
  return page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
}

export interface TouchTarget {
  description: string;
  width: number;
  height: number;
  x: number;
  y: number;
}

/** Boîtes des éléments interactifs visibles (liens, boutons, champs, contrôles ARIA). */
export async function touchTargets(page: Page): Promise<TouchTarget[]> {
  return page.evaluate(() => {
    const selector =
      "a[href], button, input:not([type=hidden]), select, textarea, [role=button], [role=link], [tabindex]:not([tabindex='-1'])";
    return [...document.querySelectorAll<HTMLElement>(selector)]
      .filter((el) => {
        const style = getComputedStyle(el);
        const box = el.getBoundingClientRect();
        return style.visibility !== "hidden" && style.display !== "none" && box.width > 0;
      })
      .map((el) => {
        const box = el.getBoundingClientRect();
        const name = el.getAttribute("aria-label") ?? el.textContent?.trim() ?? "";
        const label = el.id ? document.querySelector(`label[for="${el.id}"]`)?.textContent : null;
        return {
          description: `<${el.tagName.toLowerCase()}> « ${(label ?? name).slice(0, 60)} »`,
          width: Math.round(box.width * 10) / 10,
          height: Math.round(box.height * 10) / 10,
          x: box.x,
          y: box.y,
        };
      });
  });
}

/** Cibles plus petites que 48 × 48 px, décrites pour le message d'échec. */
export function undersized(targets: TouchTarget[]): string[] {
  return targets
    .filter((t) => t.width < MIN_TOUCH_PX || t.height < MIN_TOUCH_PX)
    .map((t) => `${t.description} : ${String(t.width)} × ${String(t.height)} px`);
}

/** Paires de cibles séparées de moins de 8 px (bord à bord, verticalement ou horizontalement). */
export function tooClose(targets: TouchTarget[]): string[] {
  const problems: string[] = [];
  targets.forEach((a, i) => {
    for (const b of targets.slice(i + 1)) {
      const gapX = Math.max(b.x - (a.x + a.width), a.x - (b.x + b.width));
      const gapY = Math.max(b.y - (a.y + a.height), a.y - (b.y + b.height));
      const gap = Math.max(gapX, gapY);
      if (gap < MIN_GAP_PX) {
        problems.push(`${a.description} ↔ ${b.description} : ${gap.toFixed(1)} px`);
      }
    }
  });
  return problems;
}
