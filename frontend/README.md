# Frontend — Gestion de boutique

PWA React 18 + TypeScript strict + Vite + Tailwind CSS v4. Identité visuelle : `../design-system.md`
(les seuls tokens autorisés sont dans `src/shared/ui/tokens.css`). Node ≥ 24.

```bash
npm ci                     # installe les versions verrouillées (package-lock.json)
cp .env.example .env       # VITE_API_BASE=/api
npm run dev                # http://localhost:5173 — vitrine des composants : /_ui
```

| Commande                            | Rôle                                                                                                                                                                              |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `npm run dev` / `build` / `preview` | développement, build de production (`dist/`), aperçu du build                                                                                                                     |
| `npm run lint`                      | ESLint + règles du design system (pas de classe arbitraire `[…]`, pas de `style=`, pas de `text-xs/sm`, pas de `<button>/<input>/<select>/<textarea>` bruts dans `src/features/`) |
| `npm run typecheck`                 | `tsc -b` (strict, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`)                                                                                                       |
| `npm run format` / `format:check`   | Prettier                                                                                                                                                                          |
| `npm test` / `test:coverage`        | vitest (jsdom) ; couverture ≥ 90 % exigée sur `src/shared/`                                                                                                                       |
| `npm run size`                      | size-limit après `build` : `dist/` ≤ 3 Mo, JS initial ≤ 250 Ko gzip                                                                                                               |
| `npm run check:length`              | échoue si un `.ts/.tsx` de `src/` dépasse 200 lignes                                                                                                                              |
| `npm run check:no-showcase`         | après `build` : prouve que `/_ui` est absent de `dist/`                                                                                                                           |
| `npm run icons`                     | régénère les icônes PWA **provisoires** depuis les tokens                                                                                                                         |

Arborescence : `src/app/` (routeur, pages, vitrine `dev/`), `src/shared/ui/` (tokens, composants),
`src/shared/format/` (montant, date, heure, quantité), `src/core/` et `src/features/` (à venir),
`src/sw.ts` (service worker : précache, nouvelle version activée au prochain lancement).
