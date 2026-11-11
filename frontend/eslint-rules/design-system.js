/**
 * Règles du design system vérifiées en CI (design-system.md § 9.2), réunies dans un bloc
 * de configuration ESLint « flat » réutilisé par eslint.config.js et par les tests.
 */
import noArbitraryTailwind from "./no-arbitrary-tailwind.js";

export const plugin = { rules: { "no-arbitrary-tailwind": noArbitraryTailwind } };

/** § 9.2-1 : pas de `style={{…}}` inline (les couleurs et tailles passent par les tokens). */
const NO_INLINE_STYLE = {
  selector: "JSXAttribute[name.name='style']",
  message:
    "Attribut style interdit : utilisez les classes issues des tokens (design-system.md § 9.2).",
};

/** § 9.2-3 : dans features/, les contrôles bruts sont refusés (composants de shared/ui). */
const NO_RAW_CONTROLS = {
  selector: "JSXOpeningElement[name.name=/^(button|input|select|textarea)$/]",
  message:
    "Élément brut interdit dans features/ : utilisez un composant de shared/ui (design-system.md § 9.2).",
};

export const designSystemConfig = [
  {
    files: ["src/**/*.{ts,tsx}"],
    plugins: { "design-system": plugin },
    rules: {
      "design-system/no-arbitrary-tailwind": "error",
      "no-restricted-syntax": ["error", NO_INLINE_STYLE],
    },
  },
  {
    // Ce bloc remplace le précédent pour features/ : il doit donc répéter NO_INLINE_STYLE.
    files: ["src/features/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-syntax": ["error", NO_INLINE_STYLE, NO_RAW_CONTROLS],
    },
  },
];
