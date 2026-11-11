/**
 * Accessibilité (design-system.md § 8, recette A11Y-01, A11Y-07) : axe-core dans le vrai
 * navigateur, règle `color-contrast` ACTIVE (contrairement à jsdom côté vitest).
 */
import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

const BLOCKING = new Set(["serious", "critical"]);

export interface BlockingViolation {
  id: string;
  impact: string;
  help: string;
  targets: string[];
}

/** Violations « serious » / « critical » de la page (WCAG 2.x A/AA + bonnes pratiques). */
export async function blockingViolations(page: Page): Promise<BlockingViolation[]> {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"])
    .analyze();
  return results.violations
    .filter((v) => v.impact !== undefined && v.impact !== null && BLOCKING.has(v.impact))
    .map((v) => ({
      id: v.id,
      impact: String(v.impact),
      help: v.help,
      targets: v.nodes.map((n) => n.target.join(" ")),
    }));
}
