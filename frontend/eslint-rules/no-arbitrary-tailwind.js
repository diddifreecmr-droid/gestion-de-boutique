/**
 * Règle locale « design-system/no-arbitrary-tailwind » (design-system.md § 9.2-1 et -2).
 *
 * Inspecte chaque chaîne littérale et chaque morceau de gabarit (`...`) d'un fichier et
 * signale les classes Tailwind :
 *  - à valeur arbitraire : `bg-[#fff]`, `p-[13px]`, `hover:text-[15px]`, `[mask:none]` ;
 *  - de taille de texte interdite : `text-xs`, `text-sm` (minimum : `text-body`).
 * Les chaînes sont découpées sur les espaces : seule une « classe » entière est jugée.
 * La forme `h-(--control-md)` (variable CSS d'un token) reste autorisée.
 */

/** Préfixes de variantes (`md:`, `hover:`, `!`) suivis d'un utilitaire `nom-[valeur]` ou `[prop:valeur]`. */
const ARBITRARY = /^(?:[a-z0-9@*-]+:)*!?(?:-?[a-z][a-z0-9-]*-\[[^\s\]]+\]|\[[a-z-]+:[^\s\]]+\])!?$/;
const FORBIDDEN_TEXT = /^(?:[a-z0-9@*-]+:)*!?text-(?:xs|sm)!?$/;

function check(context, node, text) {
  for (const token of text.split(/\s+/)) {
    if (token === "") continue;
    if (ARBITRARY.test(token)) {
      context.report({ node, messageId: "arbitrary", data: { token } });
    } else if (FORBIDDEN_TEXT.test(token)) {
      context.report({ node, messageId: "textSize", data: { token } });
    }
  }
}

export default {
  meta: {
    type: "problem",
    docs: { description: "Interdit les valeurs Tailwind arbitraires et text-xs/text-sm" },
    schema: [],
    messages: {
      arbitrary:
        "Classe « {{token}} » : valeur arbitraire interdite, utilisez un token (design-system.md § 9).",
      textSize: "Classe « {{token}} » interdite : la plus petite taille est text-body (16 px).",
    },
  },
  create(context) {
    return {
      Literal(node) {
        if (typeof node.value === "string") check(context, node, node.value);
      },
      TemplateElement(node) {
        check(context, node, node.value.cooked ?? node.value.raw);
      },
    };
  },
};
