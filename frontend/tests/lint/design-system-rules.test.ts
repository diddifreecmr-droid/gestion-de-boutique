// @vitest-environment node
/**
 * Prouve que chaque règle du design system (design-system.md § 9.2) déclenche, en lintant
 * des extraits de code avec le bloc de configuration réellement utilisé par eslint.config.js.
 */
import { ESLint } from "eslint";
import tseslint from "typescript-eslint";
import { describe, expect, it } from "vitest";
import { designSystemConfig } from "../../eslint-rules/design-system.js";

const eslint = new ESLint({
  cwd: process.cwd(),
  overrideConfigFile: true,
  overrideConfig: [
    {
      files: ["**/*.{ts,tsx}"],
      languageOptions: {
        parser: tseslint.parser,
        parserOptions: { ecmaFeatures: { jsx: true } },
      },
    },
    ...designSystemConfig,
  ],
});

async function messages(code: string, filePath = "src/shared/ui/Fixture.tsx"): Promise<string[]> {
  const [result] = await eslint.lintText(code, { filePath });
  if (result === undefined) throw new Error("ESLint n'a renvoyé aucun résultat");
  return result.messages.map((m) => `${m.ruleId ?? "fatal"}: ${m.message}`);
}

describe("règle no-arbitrary-tailwind", () => {
  it.each([
    'export const A = <div className="bg-[#fff]" />;',
    'export const A = <div className="flex p-[13px]" />;',
    'export const A = <div className="md:hover:text-[15px]" />;',
    'export const A = <div className="-mt-[2px]" />;',
    'export const A = <div className="[mask-type:luminance]" />;',
    "export const A = <div className={`gap-2 ${String(1)} w-[3rem]`} />;",
    'export const CLASSES = { primary: "bg-[rgb(0,0,0)]" };',
  ])("refuse %s", async (code) => {
    const found = await messages(code);
    expect(found).toHaveLength(1);
    expect(found[0]).toMatch(/^design-system\/no-arbitrary-tailwind: .*valeur arbitraire/);
  });

  it.each(["text-xs", "text-sm", "md:text-sm", "!text-xs"])("refuse la taille %s", async (cls) => {
    const found = await messages(`export const A = <p className="${cls}" />;`);
    expect(found).toEqual([
      `design-system/no-arbitrary-tailwind: Classe « ${cls} » interdite : la plus petite taille est text-body (16 px).`,
    ]);
  });

  it("accepte les tokens, la forme h-(--token) et les textes ordinaires", async () => {
    const code = [
      'export const A = <div className="bg-primary text-body p-4 min-h-(--control-md) text-small-caps" />;',
      'export const B = "Liste [1] et tableau[0]";',
      'export const C = "Envoi…";',
    ].join("\n");
    expect(await messages(code)).toEqual([]);
  });
});

describe("règle « pas de style inline »", () => {
  it.each(["src/shared/ui/Fixture.tsx", "src/features/sales/Fixture.tsx"])(
    "refuse style={{…}} dans %s",
    async (filePath) => {
      const found = await messages("export const A = <div style={{ color: 'red' }} />;", filePath);
      expect(found).toEqual([
        "no-restricted-syntax: Attribut style interdit : utilisez les classes issues des tokens (design-system.md § 9.2).",
      ]);
    },
  );
});

describe("règle « pas de contrôle brut dans features/ »", () => {
  it.each(["button", "input", "select", "textarea"])("refuse <%s> dans features/", async (tag) => {
    const found = await messages(`export const A = <${tag} />;`, "src/features/sales/NewSale.tsx");
    expect(found).toHaveLength(1);
    expect(found[0]).toMatch(/^no-restricted-syntax: Élément brut interdit dans features\//);
  });

  it("autorise <button> dans shared/ui et les composants Button dans features/", async () => {
    expect(await messages("export const A = <button type='button' />;")).toEqual([]);
    expect(
      await messages("export const A = <Button>Ok</Button>;", "src/features/sales/NewSale.tsx"),
    ).toEqual([]);
  });
});
