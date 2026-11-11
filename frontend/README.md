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
| `npm run gen:api` / `check:api`     | génère `src/core/api/schema.gen.ts` depuis `../backend/openapi.json` (exporté par `python -m tools.export_openapi` dans `backend/`) ; `check:api` échoue si le fichier est périmé |

Arborescence :

- `src/app/` : routeur, gardes (`guards.tsx`), coquille de boutique `/s/{shopId}/…`, pages provisoires, vitrine `dev/` ;
- `src/core/api/` : client `fetch` typé par le contrat **généré** (`schema.gen.ts`, jamais édité), `X-Device-Id` (UUIDv7 dans `localStorage`), `ApiError` / `NetworkError` ;
- `src/core/auth/` : session (jeton d'accès en mémoire, refresh **single-flight** puis rejeu, restauration silencieuse) ;
- `src/core/profile/` : `ShopProfile` (menus par rôle) — implémentation **provisoire** « motos » en dur jusqu'à `GET /shops/{id}/profile` ;
- `src/core/offline/` : connectivité (« Connexion nécessaire », aucune file d'envoi : `offline_capture` désactivé) ;
- `src/core/pwa/` : politique de cache (specs § 7.3), nouvelle version, « Recharger la dernière version », numéro de version ;
- `src/core/gateways/` : passerelles des écrans (specs § 4.6) — contrats `CatalogGateway` / `SalesGateway` calqués sur specs § 6.4, et implémentation **simulée** en mémoire (`simulated/`) branchée tant que `POST /sales` n'existe pas (remplacée en T21 dans `appGateways`, sans toucher aux écrans) ;
- `src/features/sales/` : « Nouvelle vente » comptant et crédit (`/s/{shopId}/nouvelle-vente`, chargé à la demande) ;
- `src/features/catalog/` : catalogue (UC-STK-01 à 04), onglet « Articles » de la section « Stock » du propriétaire et du comptable (`/s/{shopId}/stock?vue=articles`, fiche `?article={id}`, création `?article=nouveau`), branché sur l'API réelle via `core/gateways/httpCatalogAdmin.ts` ;
- `src/features/stock/` : section « Stock » (chargée à la demande, API réelle via `core/gateways/httpStock.ts`) — matrice (UC-STK-05, écran d'arrivée du propriétaire, du comptable et du vendeur), et pour le propriétaire et le comptable seulement : historique d'un article (`?vue=mouvements&id=`), ajustement (`?vue=ajustement`), inventaire (`?vue=inventaire[&id=]`), valeur du stock (`?vue=valeur`), stock abîmé (`?vue=abime`). Ce que voit chaque rôle passe par `stockView.ts` (le type de la vue vendeur n'a aucun champ de coût). **360 px** : la matrice est rendue en **cartes par article** (un lieu par ligne, puis « En route » et « Total ») et non en table : une table article × lieux ne tient pas à 360 px, et une table défilante cacherait les colonnes ; aucune largeur fixe, libellés et valeurs passent à la ligne. Inventaire : la quantité théorique n'est jamais lue pendant le comptage ; elle apparaît après validation (le serveur désigne d'abord les écarts sans motif, sans révéler le théorique, puis l'écran des écarts s'affiche) ;
- `src/features/purchasing/` : section « Achats » (chargée à la demande, API réelle via `core/gateways/httpPurchasing.ts`), entrée « Achats » du comptable et « Plus → Achats » du propriétaire ; vendeur et chauffeur : « Page introuvable », aucun appel. Vues dans l'adresse (`purchasingNav.ts`) : liste (`/s/{id}/achats`, mois en cours, totaux du serveur, « Afficher plus »), `?vue=nouvel` (saisie **sur un seul écran** : fournisseur avec création rapide, date, lieu, lignes, « Plus de détails » pour frais / facture / note, récapitulatif), `?vue=fiche|corriger|paiement&id=`, `?vue=fournisseurs|fournisseur|fournisseur-nouveau|fournisseur-modifier`. « Créer l'article » réutilise `catalog/ArticleCreateForm` dans le flux. **Coût unitaire final** : calculé côté écran à titre **indicatif** pendant la saisie (`costing.ts`, même règle que `backend/app/domain/purchasing/costing.py` : total de ligne et coût au franc le plus proche demi vers le haut, frais au prorata avec le reste à la ligne de plus forte valeur, yards → mètres au dixième), puis la fiche n'affiche que les chiffres de la réponse. Écart de prix (`PRICE_GAP_CONFIRMATION_REQUIRED`) : confirmation explicite puis renvoi avec `confirm_price_gap: true` et le même `id`. Lieu par défaut : réglages lus par le propriétaire ; le comptable (qui ne lit pas les réglages) envoie « lieu habituel » et le serveur l'applique. Délai du comptable (J+7) revérifié en jour métier de Douala ;
- `src/features/auth/` (connexion, connexion admin, changement de code), `src/features/settings/` (Mon compte / Réglages provisoires) ;
- `src/shared/ui/`, `src/shared/format/` ; `src/sw.ts` (service worker) ; `src/testing/` (faux serveur, axe — tests seulement).

Développement de bout en bout : backend sur `127.0.0.1:8000` (voir `../backend/README.md`), `npm run dev` relaie `/api`.
Version affichée : `APP_VERSION` au build, sinon `<version>+<date UTC>`.
